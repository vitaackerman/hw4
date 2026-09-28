import { useEffect, useState, type CSSProperties, type PointerEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { categoryOf, fetchProduct, formatPrice, type Product } from '../api'
import { askChat } from '../chatEvents'
import ProductImage from '../components/ProductImage'

// Stock bars are drawn against the largest quantity any size holds in the catalogue.
const FULL_SHELF = 25

function stockLabel(quantity: number) {
  if (quantity === 0) return 'Sold out'
  if (quantity <= 5) return `Only ${quantity} left`
  return `${quantity} in stock`
}

export default function ProductDetail() {
  const { productId = '' } = useParams()
  // Results are tagged with the id they were fetched for, so switching products shows "loading" without resetting state in the effect.
  const [result, setResult] = useState<{ id: string; product?: Product; error?: 'not-found' | 'error' } | null>(null)
  const [selection, setSelection] = useState<{ id: string; size: string } | null>(null)
  const [zoom, setZoom] = useState<{ x: number; y: number } | null>(null)

  useEffect(() => {
    fetchProduct(productId)
      .then((product) => setResult({ id: productId, product }))
      .catch((err: Error) => setResult({ id: productId, error: err.message === 'not-found' ? 'not-found' : 'error' }))
  }, [productId])

  const current = result?.id === productId ? result : null
  const product = current?.product
  const status = !current ? 'loading' : (current.error ?? 'ready')
  const selectedSize = selection?.id === productId ? selection.size : null

  if (status === 'loading') return <div className="page muted">Loading…</div>
  if (status !== 'ready' || !product) {
    return (
      <div className="page">
        <p className="notice">
          {status === 'not-found' ? "Couldn't find that product." : 'Cant reach the shop right now. Is the backend running?'}
        </p>
        <Link to="/products" className="text-link">
          Back to products
        </Link>
      </div>
    )
  }

  const category = categoryOf(product.garment_type)
  const selected = product.inventory.find((item) => item.size === selectedSize)
  const inStock = product.inventory.filter((item) => item.quantity > 0).length

  function onZoomMove(event: PointerEvent<HTMLDivElement>) {
    if (event.pointerType !== 'mouse') return
    const box = event.currentTarget.getBoundingClientRect()
    setZoom({ x: ((event.clientX - box.left) / box.width) * 100, y: ((event.clientY - box.top) / box.height) * 100 })
  }

  return (
    <div className="page detail-page">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/products">Products</Link>
        <span aria-hidden="true">/</span>
        <Link to={`/products?category=${encodeURIComponent(category)}`}>{category}</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{product.name}</span>
      </nav>

      <div className="detail">
        <div
          className={`detail-image ${zoom ? 'is-zooming' : ''}`}
          onPointerMove={onZoomMove}
          onPointerLeave={() => setZoom(null)}
          style={zoom ? ({ '--zx': `${zoom.x}%`, '--zy': `${zoom.y}%` } as CSSProperties) : undefined}
        >
          <ProductImage src={product.image_url} alt={product.name} loading="eager" />
          <span className="zoom-hint" aria-hidden="true">
            Hover to zoom
          </span>
        </div>

        <div className="detail-info">
          <p className="detail-kind">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>

          <div className="detail-colors" aria-label="Colors">
            {product.colors.map((color) => (
              <span key={color} className="color-pill">
                {color}
              </span>
            ))}
          </div>

          <p className="detail-description">{product.description}</p>

          <div className="size-head">
            <h2>Pick your size</h2>
            <span className="muted">
              {inStock} of {product.inventory.length} sizes in stock
            </span>
          </div>
          <div className="size-grid" role="radiogroup" aria-label="Size">
            {product.inventory.map((item) => (
              <button
                key={item.size}
                role="radio"
                aria-checked={selectedSize === item.size}
                className={`size-option ${selectedSize === item.size ? 'is-selected' : ''}`}
                disabled={item.quantity === 0}
                onClick={() => setSelection({ id: productId, size: item.size })}
              >
                <strong>{item.size}</strong>
                <span className={item.quantity > 0 && item.quantity <= 5 ? 'low' : ''}>{stockLabel(item.quantity)}</span>
                <span className="stock-meter" aria-hidden="true">
                  <span style={{ width: `${Math.min(100, (item.quantity / FULL_SHELF) * 100)}%` }} />
                </span>
              </button>
            ))}
          </div>

          <button className="btn btn-block btn-buy" disabled>
            {selected ? `Size ${selected.size} selected. Checkout is coming soon` : 'Pick a size. Checkout is coming soon'}
          </button>
          <button
            className="btn btn-block btn-outline"
            onClick={() =>
              askChat(selected ? `Do you have this in ${selected.size}?` : 'Which sizes do you have in this?')
            }
          >
            Ask the chat about this
          </button>
        </div>
      </div>
    </div>
  )
}
