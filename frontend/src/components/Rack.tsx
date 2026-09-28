import { useEffect, useRef, useState, type CSSProperties, type PointerEvent } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice, type Product } from '../api'
import ProductImage from './ProductImage'

type Props = { products: Product[] }

const MAX_LEAN_DEG = 8

// A clothing rail of real products, cut out of their photos so the garments hang on the hangers.
// Hangers settle once at load; hover makes one sway; drag (mouse), swipe (touch) or the arrows browse.
export default function Rack({ products }: Props) {
  const railRef = useRef<HTMLDivElement>(null)
  const drag = useRef({ active: false, moved: false, startX: 0, startScroll: 0, lastX: 0, lastT: 0 })
  const [lean, setLean] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [swaying, setSwaying] = useState<Set<string>>(() => new Set())
  const [edges, setEdges] = useState({ atStart: true, atEnd: false })

  // Keep the arrows' enabled state in sync with the scroll position.
  function updateEdges() {
    const rail = railRef.current
    if (!rail) return
    setEdges({ atStart: rail.scrollLeft < 8, atEnd: rail.scrollLeft + rail.clientWidth > rail.scrollWidth - 8 })
  }

  useEffect(() => {
    updateEdges()
    window.addEventListener('resize', updateEdges)
    return () => window.removeEventListener('resize', updateEdges)
  }, [products.length])

  function scrollByPage(direction: 1 | -1) {
    const rail = railRef.current
    if (rail) rail.scrollBy({ left: direction * rail.clientWidth * 0.75, behavior: 'smooth' })
  }

  // Sway runs to the end once started (class removed on animationend), so leaving mid-swing can't make it jump.
  const startSway = (id: string) => setSwaying((current) => (current.has(id) ? current : new Set(current).add(id)))
  const endSway = (id: string) =>
    setSwaying((current) => {
      const next = new Set(current)
      next.delete(id)
      return next
    })

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    // Touch and pen scroll natively; the custom drag is for mice.
    if (event.pointerType !== 'mouse' || event.button !== 0 || !railRef.current) return
    drag.current = {
      active: true,
      moved: false,
      startX: event.clientX,
      startScroll: railRef.current.scrollLeft,
      lastX: event.clientX,
      lastT: performance.now(),
    }
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    const d = drag.current
    const rail = railRef.current
    if (!d.active || !rail) return
    const dx = event.clientX - d.startX
    if (!d.moved && Math.abs(dx) > 6) {
      d.moved = true
      setDragging(true)
      rail.setPointerCapture(event.pointerId)
    }
    if (!d.moved) return
    rail.scrollLeft = d.startScroll - dx
    const now = performance.now()
    const velocity = (event.clientX - d.lastX) / Math.max(now - d.lastT, 1)
    setLean(Math.max(-MAX_LEAN_DEG, Math.min(MAX_LEAN_DEG, -velocity * 5)))
    d.lastX = event.clientX
    d.lastT = now
  }

  function endDrag() {
    if (!drag.current.active) return
    drag.current.active = false
    setLean(0)
    setDragging(false)
  }

  return (
    <div className="rack" style={{ '--lean': `${lean}deg` } as CSSProperties}>
      <div className="rack-controls">
        <p className="rack-hint">
          <span className="hint-mouse">Drag the rail or use the arrows to see more</span>
          <span className="hint-touch">Swipe the rail to see more</span>
        </p>
        <div className="rack-arrows">
          <button className="rack-arrow" onClick={() => scrollByPage(-1)} disabled={edges.atStart} aria-label="Previous products">
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
              <path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <button className="rack-arrow" onClick={() => scrollByPage(1)} disabled={edges.atEnd} aria-label="More products">
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
              <path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>

      <div className={`rack-stage ${edges.atStart ? '' : 'fade-start'} ${edges.atEnd ? '' : 'fade-end'}`}>
        <div className="rack-rod" aria-hidden="true" />
        <div
          className={`rack-rail ${dragging ? 'is-dragging' : ''}`}
          ref={railRef}
          onScroll={updateEdges}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          onLostPointerCapture={endDrag}
          onClickCapture={(event) => {
            // The click that ends a drag shouldn't open a product.
            if (drag.current.moved) {
              event.preventDefault()
              event.stopPropagation()
              drag.current.moved = false
            }
          }}
          role="region"
          aria-label="Featured products"
        >
          {products.map((product, index) => (
            <Link
              key={product.product_id}
              to={`/products/${product.product_id}`}
              className="hanger"
              style={{ '--i': index } as CSSProperties}
              draggable={false}
              onPointerEnter={(event) => event.pointerType === 'mouse' && !dragging && startSway(product.product_id)}
            >
              <span
                className={`hanger-body ${swaying.has(product.product_id) ? 'is-swaying' : ''}`}
                onAnimationEnd={(event) => event.animationName === 'sway' && endSway(product.product_id)}
              >
                <svg className="hanger-hook" viewBox="0 0 120 50" aria-hidden="true">
                  <path
                    d="M60 3c6 0 10 4 10 9s-4 8-10 10v6L114 46H6l54-18"
                    fill="none"
                    strokeWidth="3.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <span className="hanger-garment">
                  <ProductImage src={product.image_url} alt="" loading="eager" />
                </span>
              </span>
              <span className="hanger-tag">
                <span className="hanger-tag-name">{product.name}</span>
                <span className="hanger-tag-price">{formatPrice(product.price)}</span>
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
