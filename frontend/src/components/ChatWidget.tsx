import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  SessionExpiredError,
  fetchChatHistory,
  formatPrice,
  sendChat,
  type ChatProductCard,
  type ChatTurn,
  type PageContext,
  type User,
} from '../api'
import { onAskChat } from '../chatEvents'
import ProductImage from './ProductImage'
import { useAuth } from '../useAuth'
import { useChatResults } from '../useChatResults'

type Message = {
  id: number
  role: 'user' | 'assistant'
  content: string
  products?: ChatProductCard[]
  // "Which one do you mean?" choices; only the latest message's choices stay clickable.
  options?: ChatProductCard[]
  // Set when this reply put a result grid on the page.
  resultsSummary?: { count: number; query: string }
  // Error bubbles are shown but never sent back to the agent as history.
  isError?: boolean
}

// The chat belongs to one session: `owner` is the session token (null = guest), so logging in or out
// swaps to that person's chat without resetting state inside an effect.
type ChatState = { owner: string | null; messages: Message[]; loading: boolean }

// Matches backend models.MAX_HISTORY_MESSAGES.
const MAX_HISTORY = 20

const SUGGESTIONS = ['What hoodies do you have?', 'Is the big Yale crewneck in stock?', 'Something for The Game?']

// Status line under the typing dots, by seconds waited, so a slow answer never looks frozen.
const THINKING_STEPS: [number, string][] = [
  [0, 'Checking the catalogue…'],
  [3, 'Looking up prices and stock…'],
  [8, 'Still working on it, almost there…'],
]

let nextId = 1

function greeting(user: User | null): Message {
  return {
    id: nextId++,
    role: 'assistant',
    content: user
      ? `Hey ${user.first_name}! Welcome back. Ask me anything about our Yale gear.`
      : "Hey! I'm the Campus Customs helper. Ask me anything about our Yale gear.",
  }
}

// Tells the backend which page the shopper is on. Only ids and fixed labels; it looks up names itself.
function pageContext(pathname: string, search: string): PageContext {
  const product = pathname.match(/^\/products\/([^/]+)$/)
  if (product) return { kind: 'product', product_id: decodeURIComponent(product[1]) }
  if (pathname === '/products') return { kind: 'products', category: new URLSearchParams(search).get('category') ?? undefined }
  const kinds: Record<string, PageContext['kind']> = {
    '/': 'home',
    '/about': 'about',
    '/login': 'login',
    '/create-account': 'create-account',
  }
  return { kind: kinds[pathname] ?? 'other' }
}

// Older saved replies use **bold** markdown; render just that, everything else stays plain text.
function renderContent(text: string): ReactNode {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  )
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [waitedSeconds, setWaitedSeconds] = useState(0)
  // Synchronous lock: React state updates too late to stop a fast double-Enter or double-click.
  const sendingRef = useRef(false)
  const { user, token, signOut } = useAuth()
  const [chat, setChat] = useState<ChatState>(() => ({ owner: null, messages: [greeting(null)], loading: false }))
  const { showResults } = useChatResults()
  const location = useLocation()
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // If the session changed (login/logout) the stored chat belongs to someone else, so start fresh.
  const current: ChatState =
    chat.owner === token ? chat : { owner: token, messages: [greeting(user)], loading: token !== null }
  const messages = current.messages

  // Logged-in customers: reload their saved chat from the server whenever the session changes.
  useEffect(() => {
    if (!token) return
    let cancelled = false
    fetchChatHistory(token)
      .then(({ messages: saved }) => {
        if (cancelled) return
        const restored: Message[] = saved.map((m) => ({ id: nextId++, role: m.role, content: m.content, products: m.products }))
        setChat({ owner: token, messages: [greeting(user), ...restored], loading: false })
      })
      .catch((err: Error) => {
        if (cancelled) return
        if (err instanceof SessionExpiredError) return signOut()
        setChat({
          owner: token,
          messages: [greeting(user), { id: nextId++, role: 'assistant', content: `Couldn't load your earlier chats: ${err.message}`, isError: true }],
          loading: false,
        })
      })
    return () => {
      cancelled = true
    }
    // user and signOut only change together with the session, so this runs once per login.
  }, [token, user, signOut])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, thinking])

  useEffect(() => {
    if (open && !thinking) inputRef.current?.focus()
  }, [open, thinking])

  // Count seconds while waiting so the status line can move to the next step.
  useEffect(() => {
    if (!thinking) return
    const started = Date.now()
    const timer = window.setInterval(() => setWaitedSeconds(Math.floor((Date.now() - started) / 1000)), 500)
    return () => window.clearInterval(timer)
  }, [thinking])

  // "Ask the chat about this" buttons elsewhere open the chat with a draft the shopper can edit or send.
  useEffect(
    () =>
      onAskChat((draft) => {
        setOpen(true)
        setInput(draft)
        window.setTimeout(() => inputRef.current?.focus(), 50)
      }),
    [],
  )

  const thinkingText = [...THINKING_STEPS].reverse().find(([after]) => waitedSeconds >= after)?.[1] ?? THINKING_STEPS[0][1]
  const busy = thinking || current.loading

  function append(owner: string | null, message: Message) {
    // Drop late replies if the user logged in/out while waiting.
    setChat((prev) => (prev.owner === owner ? { ...prev, messages: [...prev.messages, message] } : prev))
  }

  async function send(text: string) {
    const content = text.trim()
    if (!content || sendingRef.current || current.loading) return
    sendingRef.current = true
    const owner = token
    // Guests send their in-memory history; for logged-in users the server uses the saved history.
    const history: ChatTurn[] = owner
      ? []
      : messages
          .filter((message) => !message.isError)
          .slice(-MAX_HISTORY)
          .map(({ role, content }) => ({ role, content }))
    setChat({ ...current, messages: [...messages, { id: nextId++, role: 'user', content }] })
    setInput('')
    setWaitedSeconds(0)
    setThinking(true)
    try {
      const reply = await sendChat(content, history, pageContext(location.pathname, location.search), owner)
      const results = reply.search_results
      if (results && results.products.length > 0) showResults(results)
      append(owner, {
        id: nextId++,
        role: 'assistant',
        content: reply.reply,
        products: reply.products,
        options: reply.clarification_options,
        resultsSummary: results?.products.length ? { count: results.total_matches, query: results.query } : undefined,
      })
    } catch (err) {
      if (err instanceof SessionExpiredError) {
        signOut()
        return
      }
      append(owner, { id: nextId++, role: 'assistant', content: (err as Error).message, isError: true })
    } finally {
      sendingRef.current = false
      setThinking(false)
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    send(input)
  }

  return (
    <div className={`chat ${open ? 'is-open' : ''}`}>
      {open && (
        <section className="chat-panel" aria-label="Campus Customs chat" aria-busy={busy}>
          <header className="chat-header">
            <div>
              <strong>Campus Customs Chat</strong>
              <span className="chat-status">
                <span className={`chat-dot ${thinking ? 'is-busy' : ''}`} />{' '}
                {thinking
                  ? 'Typing…'
                  : user
                    ? `Chatting as ${user.first_name}, your chat is saved`
                    : 'Guest chat. Log in to save it'}
              </span>
            </div>
            <button className="chat-close" aria-label="Close chat" onClick={() => setOpen(false)}>
              ×
            </button>
          </header>

          <div className="chat-messages" ref={listRef}>
            {messages.map((message) => (
              <div key={message.id} className={`chat-turn chat-turn-${message.role}`}>
                <div className={`chat-bubble chat-${message.role} ${message.isError ? 'chat-error' : ''}`}>
                  {renderContent(message.content)}
                </div>
                {message.resultsSummary && (
                  <button
                    className="chat-results-link"
                    onClick={() => document.getElementById('chat-results')?.scrollIntoView({ behavior: 'smooth' })}
                  >
                    Showing {message.resultsSummary.count} {message.resultsSummary.count === 1 ? 'match' : 'matches'} on
                    the page ↑
                  </button>
                )}
                {message.options && message.options.length > 0 && (
                  <div className="chat-options" role="group" aria-label="Which one do you mean?">
                    {message.options.map((option) => (
                      <button
                        key={option.product_id}
                        className="chat-option"
                        disabled={busy || message.id !== messages.at(-1)?.id}
                        onClick={() => send(`I mean the ${option.name}`)}
                      >
                        <ProductImage src={option.image_url} alt="" />
                        <span className="chat-product-name">{option.name}</span>
                        <span className="chat-product-meta">{formatPrice(option.price)}</span>
                      </button>
                    ))}
                  </div>
                )}
                {message.products && message.products.length > 0 && (
                  <div className="chat-products">
                    {message.products.map((product) => (
                      <Link key={product.product_id} to={`/products/${product.product_id}`} className="chat-product">
                        <ProductImage src={product.image_url} alt="" />
                        <span className="chat-product-name">{product.name}</span>
                        <span className="chat-product-meta">
                          {formatPrice(product.price)}
                          {product.total_stock === 0 && ', sold out'}
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {thinking && (
              <div className="chat-turn chat-turn-assistant" role="status" aria-live="polite">
                <div className="chat-bubble chat-assistant chat-typing" aria-label="Assistant is typing">
                  <span />
                  <span />
                  <span />
                </div>
                <span className="chat-thinking-text">{thinkingText}</span>
              </div>
            )}
          </div>

          {current.loading && <p className="chat-loading">Loading your earlier chats…</p>}

          {messages.length === 1 && !current.loading && (
            <div className="chat-suggestions">
              {SUGGESTIONS.map((suggestion) => (
                <button key={suggestion} onClick={() => send(suggestion)} disabled={busy}>
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          <form className="chat-input" onSubmit={onSubmit}>
            <input
              ref={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={thinking ? 'Waiting for the reply…' : 'Ask about sizes, stock, gifts…'}
              aria-label="Message"
              disabled={busy}
            />
            <button
              type="submit"
              disabled={!input.trim() || busy}
              aria-label={thinking ? 'Waiting for reply' : 'Send message'}
              className={thinking ? 'is-sending' : ''}
            >
              {thinking ? (
                <span className="chat-spinner" aria-hidden="true" />
              ) : (
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                  <path d="M3 20.5 21 12 3 3.5l2.8 7.1L15 12l-9.2 1.4z" fill="currentColor" />
                </svg>
              )}
            </button>
          </form>
        </section>
      )}

      <button className="chat-launcher" aria-label={open ? 'Close chat' : 'Open chat'} onClick={() => setOpen((v) => !v)}>
        {open ? (
          <span className="chat-launcher-x" aria-hidden="true">
            ×
          </span>
        ) : (
          <span className="chat-patch" aria-hidden="true">
            Y
          </span>
        )}
        {!open && <span className="chat-launcher-label">Ask us</span>}
      </button>
    </div>
  )
}
