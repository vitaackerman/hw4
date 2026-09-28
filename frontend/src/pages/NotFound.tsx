import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="page auth-page">
      <div className="auth-card">
        <h1>Page not found</h1>
        <p className="muted">That page doesnt exist. Maybe it graduated.</p>
        <Link to="/" className="btn btn-block">
          Back home
        </Link>
      </div>
    </div>
  )
}
