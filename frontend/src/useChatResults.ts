import { createContext, useContext } from 'react'
import type { ChatSearchResults } from './api'

export type ChatResultsValue = {
  results: ChatSearchResults | null
  // Bumped on every new result set so the page can scroll to it, even for a repeated search.
  version: number
  showResults: (results: ChatSearchResults) => void
  clearResults: () => void
}

export const ChatResultsContext = createContext<ChatResultsValue | null>(null)

export function useChatResults() {
  const value = useContext(ChatResultsContext)
  if (!value) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return value
}
