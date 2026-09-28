import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { loginUser } from '../api'
import { useAuth } from '../useAuth'

export default function Login() {
  const { user, signIn, signOut } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [justLoggedIn, setJustLoggedIn] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const session = await loginUser({ email, password })
      signIn(session.user, session.token)
      setJustLoggedIn(true)
      setPassword('')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  if (user) {
    return (
      <div className="page auth-page">
        <div className="auth-card">
          <h1>Hi, {user.first_name}!</h1>
          <p className="notice notice-success" role="status">
            {justLoggedIn ? "You're logged in" : "You're already logged in"} as <strong>{user.email}</strong>.
          </p>
          <Link to="/products" className="btn btn-block">
            Start shopping
          </Link>
          <button className="btn btn-block btn-outline" onClick={signOut}>
            Log out
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="page auth-page">
      <form className="auth-card" onSubmit={onSubmit}>
        <h1>Log in</h1>
        <p className="muted">Log in to keep your chats and see whats in your size.</p>

        {error && (
          <p className="notice notice-error" role="alert">
            {error}
          </p>
        )}

        <label>
          Email
          <input
            type="email"
            name="email"
            autoComplete="email"
            placeholder="you@yale.edu"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        <button type="submit" className="btn btn-block" disabled={submitting}>
          {submitting ? 'Logging in…' : 'Log in'}
        </button>

        <p className="auth-switch">
          New here? <Link to="/create-account">Create an account</Link>
        </p>
      </form>
    </div>
  )
}
