// Lets any page open the chat with a question already typed (e.g. "Ask the chat about this" on a product page).
const EVENT = 'campus-customs:ask-chat'

export function askChat(draft: string) {
  window.dispatchEvent(new CustomEvent<string>(EVENT, { detail: draft }))
}

export function onAskChat(handler: (draft: string) => void): () => void {
  const listener = (event: Event) => handler((event as CustomEvent<string>).detail)
  window.addEventListener(EVENT, listener)
  return () => window.removeEventListener(EVENT, listener)
}
