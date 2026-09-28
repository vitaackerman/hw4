import { createContext, useContext } from 'react'
import type { User } from './api'

export type AuthContextValue = {
  user: User | null
  // Signed session token from the backend; sent as "Authorization: Bearer <token>".
  token: string | null
  signIn: (user: User, token: string) => void
  signOut: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
