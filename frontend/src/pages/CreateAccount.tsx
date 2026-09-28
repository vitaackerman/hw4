import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { registerUser, type RegisterInput } from '../api'
import { useAuth } from '../useAuth'

const EMPTY_FORM: RegisterInput = { first_name: '', last_name: '', email: '', password: '' }

export default function CreateAccount() {
  const { user, signIn, signOut } = useAuth()
  const [form, setForm] = useState<RegisterInput>(EMPTY_FORM)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [justCreated, setJustCreated] = useState(false)

  const update = (field: keyof RegisterInput) => (event: ChangeEvent<HTMLInputElement>) =>
    setForm((current) => ({ ...current, [field]: event.target.value }))

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      // New accounts are logged in straight away.
      const session = await registerUser(form)
      signIn(session.user, session.token)
      setJustCreated(true)
      setForm(EMPTY_FORM)
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
          <h1>{justCreated ? `Welcome, ${user.first_name}!` : `Hi, ${user.first_name}!`}</h1>
          <p className="notice notice-success" role="status">
            {justCreated ? "Your account is all set and you're logged in" : "You're already logged in"} as{' '}
            <strong>{user.email}</strong>.
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
        <h1>Create account</h1>
        <p className="muted">Takes like 30 seconds. Then the chat can remember what you were looking at.</p>

        {error && (
          <p className="notice notice-error" role="alert">
            {error}
          </p>
        )}

        <div className="auth-row">
          <label>
            First name
            <input
              name="first_name"
              autoComplete="given-name"
              value={form.first_name}
              onChange={update('first_name')}
              required
            />
          </label>
          <label>
            Last name
            <input
              name="last_name"
              autoComplete="family-name"
              value={form.last_name}
              onChange={update('last_name')}
              required
            />
          </label>
        </div>
        <label>
          Email
          <input
            type="email"
            name="email"
            autoComplete="email"
            placeholder="you@yale.edu"
            value={form.email}
            onChange={update('email')}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="new-password"
            minLength={8}
            value={form.password}
            onChange={update('password')}
            required
          />
          <span className="field-hint">At least 8 characters.</span>
        </label>

        <button type="submit" className="btn btn-block" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>

        <p className="auth-switch">
          Already have one? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  )
}
