import { useCallback, useState, type ReactNode } from 'react'
import type { User } from './api'
import { AuthContext } from './useAuth'

const STORAGE_KEY = 'campus-customs-user'

type Session = { user: User; token: string }

function loadSession(): Session | null {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
    // Sessions saved before tokens existed ({...user} with no token) count as logged out.
    return saved?.user && typeof saved.token === 'string' ? (saved as Session) : null
  } catch {
    return null
  }
}

// Keeps the logged-in user's public profile and session token so they survive a page refresh.
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(loadSession)

  const signIn = useCallback((user: User, token: string) => {
    const next = { user, token }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    setSession(next)
  }, [])

  const signOut = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setSession(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user: session?.user ?? null, token: session?.token ?? null, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}
