import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import type { ProductMatch } from '../api'
import { useChatResults } from '../useChatResults'
import ProductCard from './ProductCard'

// Pages where a results grid on top would push the actual content down.
const HIDDEN_ON = [/^\/products\/[^/]+$/, /^\/login$/, /^\/create-account$/]

const toCard = (match: ProductMatch) => ({
  product_id: match.product_id,
  name: match.name,
  price: match.price,
  image_url: match.image_url,
  short_info: match.short_description,
  total_stock: match.total_stock,
})

export default function ChatResultsPanel() {
  const { results, version, clearResults } = useChatResults()
  const { pathname } = useLocation()
  const panelRef = useRef<HTMLElement>(null)
  const hidden = HIDDEN_ON.some((pattern) => pattern.test(pathname))

  // Bring each new result set into view.
  useEffect(() => {
    if (version > 0) panelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [version])

  if (!results || hidden) return null

  return (
    <section className="chat-results" ref={panelRef} id="chat-results" aria-live="polite">
      <div className="chat-results-inner">
        <header className="chat-results-head">
          <div>
            <p className="chat-results-kicker">Found by the chat</p>
            <h2>
              {results.total_matches} {results.total_matches === 1 ? 'match' : 'matches'} for “{results.query}”
            </h2>
          </div>
          <button className="btn btn-small btn-outline" onClick={clearResults}>
            Clear results
          </button>
        </header>
        <div className="product-grid">
          {results.products.map((match) => (
            <ProductCard key={match.product_id} product={toCard(match)} />
          ))}
        </div>
      </div>
    </section>
  )
}
