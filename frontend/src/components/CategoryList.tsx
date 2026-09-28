import { useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { CATEGORIES, categoryOf, formatPrice, type Product } from '../api'
import ProductImage from './ProductImage'

const BLURBS: Record<string, string> = {
  Hoodies: 'The one you live in',
  Crewnecks: 'Lecture-ready',
  Tees: 'Game day basics',
  'Quarter-zips': 'Looks like you have a plan',
  'Jackets & fleece': 'For the Cross Campus wind',
}

// Category rows on the left, a "display window" on the right: hovering or focusing a row deals
// three real garments from that category onto the stage. The text never moves or gets covered.
export default function CategoryList({ products }: { products: Product[] }) {
  const [active, setActive] = useState<string>(CATEGORIES[0])

  const groups = CATEGORIES.map((category) => {
    const items = products.filter((p) => categoryOf(p.garment_type) === category)
    const showcase = items
      .filter((p) => p.has_cutout)
      .sort((a, b) => b.total_stock - a.total_stock)
      .slice(0, 3)
    return {
      category,
      count: items.length,
      fromPrice: items.length ? Math.min(...items.map((p) => p.price)) : null,
      showcase,
    }
  })
  const current = groups.find((g) => g.category === active) ?? groups[0]
  const categoryLink = (category: string) => `/products?category=${encodeURIComponent(category)}`

  return (
    <div className="category-browser">
      <div className="category-list" role="list">
        {groups.map(({ category, count, showcase }) => (
          <Link
            key={category}
            role="listitem"
            to={categoryLink(category)}
            className={`category-tile ${active === category ? 'is-active' : ''}`}
            onPointerEnter={() => setActive(category)}
            onFocus={() => setActive(category)}
          >
            {showcase[0] && <ProductImage className="category-thumb" src={showcase[0].image_url} alt="" />}
            <span className="category-name">{category}</span>
            <span className="category-blurb">{BLURBS[category]}</span>
            <span className="category-count">{count} styles</span>
          </Link>
        ))}
      </div>

      <div className="category-stage" aria-live="polite">
        {/* Keyed by category so each switch re-deals the fan. */}
        <div className="category-fan" key={current.category}>
          {current.showcase.map((product, index) => (
            <Link
              key={product.product_id}
              to={`/products/${product.product_id}`}
              className="fan-card"
              style={{ '--slot': index - 1 } as CSSProperties}
              aria-label={`${product.name}, ${formatPrice(product.price)}`}
            >
              <ProductImage src={product.image_url} alt="" loading="eager" />
            </Link>
          ))}
        </div>
        <Link to={categoryLink(current.category)} className="category-stage-caption">
          <span className="category-stage-name">{current.category}</span>
          <span className="muted">
            {current.count} styles{current.fromPrice !== null && `, from ${formatPrice(current.fromPrice)}`}
          </span>
        </Link>
      </div>
    </div>
  )
}
