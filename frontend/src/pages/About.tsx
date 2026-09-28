import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CATEGORIES, categoryOf, fetchProducts, type Product } from '../api'

export default function About() {
  const [products, setProducts] = useState<Product[]>([])

  useEffect(() => {
    fetchProducts().then(setProducts).catch(() => setProducts([]))
  }, [])

  return (
    <>
      <section className="about-hero">
        <div className="about-hero-inner">
          <h1>We just really like it here.</h1>
          <p>
            Campus Customs started because we wanted Yale gear that we'd actually wear, not the stiff stuff you buy
            once for your parents and never touch again.
          </p>
        </div>
      </section>

      <section className="section about-story">
        <div className="about-copy">
          <h2>How it started</h2>
          <p>
            Basically we kept getting asked where we got our hoodies. So we started making more of them. The idea was
            simple: take the things people love about being here, like the old buildings, the rivalry, the late
            nights, and put them on clothes that feel good.
          </p>
          <p>
            Now we do crewnecks, tees, quarter-zips and jackets too. Still the same idea though. If it doesn't feel
            like Yale, we dont make it.
          </p>
        </div>

        {products.length > 0 && (
          <aside className="about-shelf" aria-label="What's on the shelf">
            <h3>On the shelf right now</h3>
            <ul>
              {CATEGORIES.map((category) => {
                const count = products.filter((p) => categoryOf(p.garment_type) === category).length
                return (
                  <li key={category}>
                    <Link to={`/products?category=${encodeURIComponent(category)}`}>
                      <span>{category}</span>
                      <span className="about-shelf-count">{count}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
            <p className="muted">Every style comes in XS to XXL.</p>
          </aside>
        )}
      </section>

      <section className="section values">
        <div>
          <h3>For students first</h3>
          <p>We design for the people walking to class every day, then everyone else who loves it here.</p>
        </div>
        <div>
          <h3>Stuff that lasts</h3>
          <p>You should be able to wear it at your 10 year reunion and still get compliments.</p>
        </div>
        <div>
          <h3>Blue, always</h3>
          <p>Navy, white, and gray mostly. We keep the look classic on purpose.</p>
        </div>
      </section>

      <section className="banner">
        <div className="banner-inner">
          <h2>Come see what's new.</h2>
          <p>The fall stuff is up now. Go look before your size sells out.</p>
          <Link to="/products" className="btn btn-light">
            Shop products
          </Link>
        </div>
      </section>
    </>
  )
}
