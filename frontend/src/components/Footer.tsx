import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <p className="footer-mark">Campus Customs</p>
          <p>Yale gear from people who actually live here. Hoodies, crewnecks, tees, the whole thing.</p>
        </div>
        <nav className="footer-col" aria-label="Shop">
          <h4>Shop</h4>
          <Link to="/products">All products</Link>
          <Link to="/products?category=Hoodies">Hoodies</Link>
          <Link to="/products?category=Crewnecks">Crewnecks</Link>
          <Link to="/products?category=Tees">Tees</Link>
        </nav>
        <nav className="footer-col" aria-label="Campus Customs">
          <h4>Campus Customs</h4>
          <Link to="/about">About us</Link>
          <Link to="/login">Log in</Link>
          <Link to="/create-account">Create account</Link>
        </nav>
        <div className="footer-col">
          <h4>Visit</h4>
          <span>New Haven, CT</span>
          <span>Or just ask the chat in the corner</span>
        </div>
      </div>
      <div className="footer-bottom">
        © {new Date().getFullYear()} Campus Customs. A class project, not affiliated with Yale University.
      </div>
    </footer>
  )
}
