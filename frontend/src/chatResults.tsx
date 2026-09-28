import { useState, type ReactNode } from 'react'
import type { ChatSearchResults } from './api'
import { ChatResultsContext } from './useChatResults'

// Holds the latest product matches the chat agent found, shared by the chat widget and the page grid.
export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatSearchResults | null>(null)
  const [version, setVersion] = useState(0)

  function showResults(next: ChatSearchResults) {
    setResults(next)
    setVersion((v) => v + 1)
  }

  return (
    <ChatResultsContext.Provider value={{ results, version, showResults, clearResults: () => setResults(null) }}>
      {children}
    </ChatResultsContext.Provider>
  )
}
