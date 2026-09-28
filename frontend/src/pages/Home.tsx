import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CATEGORIES, cardFromProduct, categoryOf, fetchProducts, type Product } from '../api'
import CategoryList from '../components/CategoryList'
import ProductCard from '../components/ProductCard'
import Rack from '../components/Rack'

const RACK_SIZE = 12

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState(false)

  useEffect(() => {
    fetchProducts().then(setProducts).catch(() => setError(true))
  }, [])

  // Deal the rack like a real rail: one of each category in turn, best-stocked first.
  const rack = useMemo(() => {
    const queues = CATEGORIES.map((category) =>
      products
        // Only garments with a clean cutout hang on the rail.
        .filter((p) => p.has_cutout && categoryOf(p.garment_type) === category)
        .sort((a, b) => b.total_stock - a.total_stock),
    )
    const dealt: Product[] = []
    for (let round = 0; dealt.length < RACK_SIZE && queues.some((q) => q.length > round); round++) {
      for (const queue of queues) if (queue[round] && dealt.length < RACK_SIZE) dealt.push(queue[round])
    }
    return dealt
  }, [products])

  // Game-related items first, topped up with the best-stocked products so the row is always full.
  const picks = useMemo(() => {
    const gameDay = products.filter((p) => p.search_tags.some((tag) => /harvard|the game/i.test(tag)))
    const rest = products.filter((p) => !gameDay.includes(p)).sort((a, b) => b.total_stock - a.total_stock)
    return [...gameDay, ...rest].slice(0, 4)
  }, [products])

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <h1>Blue, all year.</h1>
          <p>
            Honestly the easiest way to look like you belong here. Hoodies, crewnecks and tees made for late nights
            at the library, cold walks to class, and screaming at The Game.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-light">
              Shop all {products.length || ''} styles
            </Link>
            <Link to="/about" className="btn btn-ghost-light">
              Our story
            </Link>
          </div>
        </div>
        {error ? (
          <p className="notice hero-notice">Cant reach the shop right now. Is the backend running?</p>
        ) : (
          rack.length > 0 && <Rack products={rack} />
        )}
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Shop by category</h2>
          <Link to="/products" className="text-link">
            View everything
          </Link>
        </div>
        <CategoryList products={products} />
      </section>

      <section className="banner">
        <div className="banner-inner">
          <h2>Beat Harvard. Obviously.</h2>
          <p>
            Its the one weekend a year where everyone wears blue on purpose. Grab something before your size is gone,
            because it always goes fast.
          </p>
          <Link to="/products?q=game" className="btn btn-light">
            Shop game day
          </Link>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Fan favorites</h2>
          <Link to="/products?sort=stock" className="text-link">
            Shop everything
          </Link>
        </div>
        <div className="product-grid">
          {picks.map((product) => (
            <ProductCard key={product.product_id} product={cardFromProduct(product)} />
          ))}
        </div>
      </section>

      <section className="section values">
        <div>
          <h3>Made for here</h3>
          <p>Every design is about Yale and New Haven. No generic college stuff.</p>
        </div>
        <div>
          <h3>Actually comfy</h3>
          <p>Heavy fleece and soft tees you'll want to wear way past graduation.</p>
        </div>
        <div>
          <h3>Ask us anything</h3>
          <p>Not sure about fit or sizing? The chat in the corner checks real stock for you.</p>
        </div>
      </section>
    </>
  )
}
