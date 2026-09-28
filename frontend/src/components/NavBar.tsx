import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../useAuth'

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products', end: false },
  { to: '/about', label: 'About Us', end: false },
]

export function Wordmark() {
  return (
    <Link to="/" className="wordmark" aria-label="Campus Customs home">
      <span className="wordmark-shield" aria-hidden="true">
        Y
      </span>
      <span className="wordmark-text">
        <span className="wordmark-name">Campus Customs</span>
        <span className="wordmark-sub">Yale apparel, New Haven</span>
      </span>
    </Link>
  )
}

export default function NavBar() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const { user, signOut } = useAuth()
  const { pathname } = useLocation()
  const linksRef = useRef<HTMLDivElement>(null)
  const indicatorRef = useRef<HTMLSpanElement>(null)
  const close = () => setOpen(false)

  // One underline that slides to whichever link is hovered, and back to the current page.
  function moveIndicator(target: HTMLElement | null) {
    const bar = indicatorRef.current
    if (!bar) return
    if (!target) {
      bar.style.opacity = '0'
      return
    }
    bar.style.opacity = '1'
    bar.style.width = `${target.offsetWidth}px`
    bar.style.transform = `translateX(${target.offsetLeft}px)`
  }
  const moveToActive = () => moveIndicator(linksRef.current?.querySelector<HTMLElement>('.nav-link.active') ?? null)

  useLayoutEffect(() => {
    moveToActive()
  }, [pathname])

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    const onResize = () => moveToActive()
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onResize)
    // Fonts load after first paint and change link widths.
    document.fonts?.ready.then(onResize)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onResize)
    }
  }, [])

  return (
    <header className={`site-header ${scrolled ? 'is-scrolled' : ''}`}>
      <div className="announcement">The fall drop is live, and The Game is coming. Gear up early.</div>
      <nav className="nav">
        <Wordmark />
        <button
          className={`nav-toggle ${open ? 'is-open' : ''}`}
          aria-label="Toggle menu"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          <span />
          <span />
          <span />
        </button>
        <div className={`nav-links ${open ? 'is-open' : ''}`}>
          <div className="nav-primary" ref={linksRef} onPointerLeave={moveToActive}>
            {LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className="nav-link"
                onClick={close}
                onPointerEnter={(event) => moveIndicator(event.currentTarget)}
              >
                {link.label}
              </NavLink>
            ))}
            <span className="nav-indicator" ref={indicatorRef} aria-hidden="true" />
          </div>
          <div className="nav-account">
            {user ? (
              <>
                <span className="nav-greeting">Hi, {user.first_name}</span>
                <button
                  className="btn btn-small btn-outline"
                  onClick={() => {
                    signOut()
                    close()
                  }}
                >
                  Log Out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className="nav-link nav-link-plain" onClick={close}>
                  Log In
                </NavLink>
                <NavLink to="/create-account" className="btn btn-small" onClick={close}>
                  Create Account
                </NavLink>
              </>
            )}
          </div>
        </div>
      </nav>
    </header>
  )
}
