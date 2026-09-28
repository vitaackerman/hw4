import { Link } from 'react-router-dom'
import { formatPrice, type CardData } from '../api'
import ProductImage from './ProductImage'

const LOW_STOCK = 10

export default function ProductCard({ product }: { product: CardData }) {
  const soldOut = product.total_stock === 0
  const lowStock = !soldOut && product.total_stock <= LOW_STOCK

  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card-image">
        <ProductImage src={product.image_url} alt={product.name} />
        {soldOut && <span className="badge badge-soldout">Sold out</span>}
        {lowStock && <span className="badge badge-low">Only {product.total_stock} left</span>}
        {product.sizes && !soldOut && (
          // Hang-tag that slides up on hover: which sizes are actually on the shelf.
          <span className="size-tag" aria-label={`Sizes in stock: ${product.sizes.filter((s) => s.quantity > 0).map((s) => s.size).join(', ')}`}>
            {product.sizes.map((s) => (
              <span key={s.size} className={s.quantity > 0 ? '' : 'is-out'}>
                {s.size}
              </span>
            ))}
          </span>
        )}
      </div>
      <div className="product-card-body">
        <div className="product-card-row">
          <h3>{product.name}</h3>
          <span className="price">{formatPrice(product.price)}</span>
        </div>
        <p>{product.short_info}</p>
      </div>
    </Link>
  )
}
