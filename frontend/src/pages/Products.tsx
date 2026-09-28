import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CATEGORIES, cardFromProduct, categoryOf, fetchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const PRICE_CAPS = [40, 60, 80]
const SORTS = {
  featured: 'Featured',
  'price-asc': 'Price: low to high',
  'price-desc': 'Price: high to low',
  name: 'Name: A to Z',
  stock: 'Most in stock',
} as const
type SortKey = keyof typeof SORTS

// The catalogue has ~25 free-text colors ("navy blue", "heather gray", "dusty coral"); group them for filtering.
const COLOR_FAMILIES: { family: string; swatch: string; words: string[] }[] = [
  { family: 'Navy', swatch: '#14284b', words: ['navy'] },
  { family: 'Gray', swatch: '#9aa0a6', words: ['gray', 'grey', 'charcoal'] },
  { family: 'White', swatch: '#ffffff', words: ['white', 'cream', 'ivory'] },
  { family: 'Blue', swatch: '#3a78c2', words: ['blue'] },
  { family: 'Red', swatch: '#c0392b', words: ['red', 'coral'] },
  { family: 'Black', swatch: '#111111', words: ['black'] },
  { family: 'Yellow', swatch: '#f2c230', words: ['yellow'] },
  { family: 'Green', swatch: '#2e8b57', words: ['green'] },
  { family: 'Gold', swatch: '#c9a227', words: ['gold'] },
]

function colorFamilies(colors: string[]): Set<string> {
  const families = new Set<string>()
  for (const color of colors.map((c) => c.toLowerCase())) {
    // "navy blue" is navy, not blue: take the first family that matches.
    const match = COLOR_FAMILIES.find(({ words }) => words.some((w) => color.includes(w)))
    if (match) families.add(match.family)
  }
  return families
}

function stockInSize(product: Product, size: string): number {
  return product.inventory.find((item) => item.size === size)?.quantity ?? 0
}

export default function Products() {
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  // Phones only: the filter panel folds away behind a button so products show on the first screen.
  const [filtersOpen, setFiltersOpen] = useState(false)

  // Every filter lives in the URL, so filtered views can be shared and the back button works.
  const query = searchParams.get('q') ?? ''
  const category = searchParams.get('category')
  const size = searchParams.get('size')
  const maxPrice = Number(searchParams.get('max')) || null
  const color = searchParams.get('color')
  const sortParam = searchParams.get('sort') ?? 'featured'
  const sort: SortKey = sortParam in SORTS ? (sortParam as SortKey) : 'featured'

  useEffect(() => {
    fetchProducts().then(setProducts).catch(() => setError(true))
  }, [])

  function setParam(key: string, value: string | null) {
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current)
        if (value) next.set(key, value)
        else next.delete(key)
        return next
      },
      // Typing in the search box shouldn't add a history entry per keystroke.
      { replace: key === 'q' },
    )
  }

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const matches = (products ?? []).filter((product) => {
      if (category && categoryOf(product.garment_type) !== category) return false
      if (size && stockInSize(product, size) === 0) return false
      if (maxPrice && product.price > maxPrice) return false
      if (color && !colorFamilies(product.colors).has(color)) return false
      if (!needle) return true
      return [product.name, product.description, ...product.colors, ...product.search_tags]
        .join(' ')
        .toLowerCase()
        .includes(needle)
    })
    const sorted = [...matches]
    if (sort === 'price-asc') sorted.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
    if (sort === 'price-desc') sorted.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
    if (sort === 'name') sorted.sort((a, b) => a.name.localeCompare(b.name))
    if (sort === 'stock') sorted.sort((a, b) => (size ? stockInSize(b, size) - stockInSize(a, size) : b.total_stock - a.total_stock))
    return sorted
  }, [products, category, size, maxPrice, color, query, sort])

  const activeFilters = [
    query && { key: 'q', label: `“${query}”` },
    category && { key: 'category', label: category },
    size && { key: 'size', label: `Size ${size} in stock` },
    maxPrice && { key: 'max', label: `Under $${maxPrice}` },
    color && { key: 'color', label: color },
  ].filter(Boolean) as { key: string; label: string }[]

  return (
    <div className="page">
      <header className="page-head">
        <h1>{category ?? 'All products'}</h1>
        <p>Everything we have right now. Use the filters to find your size and budget fast.</p>
      </header>

      <div className="toolbar">
        <div className="chips" role="group" aria-label="Categories">
          <button className={`chip ${!category ? 'is-active' : ''}`} onClick={() => setParam('category', null)}>
            All
          </button>
          {CATEGORIES.map((name) => (
            <button
              key={name}
              className={`chip ${category === name ? 'is-active' : ''}`}
              onClick={() => setParam('category', name)}
            >
              {name}
            </button>
          ))}
        </div>
        <input
          className="search"
          type="search"
          placeholder="Search hoodies, colors, The Game…"
          value={query}
          onChange={(event) => setParam('q', event.target.value || null)}
          aria-label="Search products"
        />
      </div>

      <button
        className="btn btn-small btn-outline filters-toggle"
        aria-expanded={filtersOpen}
        aria-controls="product-filters"
        onClick={() => setFiltersOpen((open) => !open)}
      >
        {filtersOpen ? 'Hide filters' : 'Size, price and color filters'}
      </button>

      <div className={`filters ${filtersOpen ? 'is-open' : ''}`} id="product-filters" role="group" aria-label="Filters">
        <div className="filter-group">
          <span className="filter-label">Size in stock</span>
          <div className="size-filter" role="group" aria-label="Size in stock">
            {SIZES.map((s) => (
              <button
                key={s}
                className={`size-chip ${size === s ? 'is-active' : ''}`}
                aria-pressed={size === s}
                onClick={() => setParam('size', size === s ? null : s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <label className="filter-group">
          <span className="filter-label">Price</span>
          <select value={maxPrice ?? ''} onChange={(event) => setParam('max', event.target.value || null)}>
            <option value="">Any price</option>
            {PRICE_CAPS.map((cap) => (
              <option key={cap} value={cap}>
                Under ${cap}
              </option>
            ))}
          </select>
        </label>

        <div className="filter-group">
          <span className="filter-label">Color</span>
          <div className="swatches" role="group" aria-label="Color">
            {COLOR_FAMILIES.map(({ family, swatch }) => (
              <button
                key={family}
                className={`swatch ${color === family ? 'is-active' : ''}`}
                style={{ background: swatch }}
                title={family}
                aria-label={family}
                aria-pressed={color === family}
                onClick={() => setParam('color', color === family ? null : family)}
              />
            ))}
          </div>
        </div>

        <label className="filter-group filter-sort">
          <span className="filter-label">Sort</span>
          <select value={sort} onChange={(event) => setParam('sort', event.target.value === 'featured' ? null : event.target.value)}>
            {Object.entries(SORTS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="notice">Cant reach the shop right now. Is the backend running on port 8000?</p>}
      {!products && !error && <p className="muted">Loading the goods…</p>}
      {products && (
        <div className="result-bar">
          <p className="muted result-count">
            {visible.length} of {products.length} products
          </p>
          {activeFilters.map((filter) => (
            <button
              key={filter.key}
              className="active-filter"
              onClick={() => setParam(filter.key, null)}
              aria-label={`Remove filter ${filter.label}`}
            >
              {filter.label} <span aria-hidden="true">×</span>
            </button>
          ))}
          {activeFilters.length > 1 && (
            <button className="text-link clear-all" onClick={() => setSearchParams({})}>
              Clear all
            </button>
          )}
        </div>
      )}
      {products && visible.length === 0 && (
        <div className="notice empty-state">
          Nothing matches all of those filters. Try removing one, or{' '}
          <button className="text-link" onClick={() => setSearchParams({})}>
            clear all filters
          </button>
          .
        </div>
      )}

      <div className="product-grid">
        {visible.map((product) => {
          const card = cardFromProduct(product)
          // With a size filter on, lead with how many are left in that size.
          const shortInfo = size ? `${stockInSize(product, size)} left in ${size}. ${card.short_info}` : card.short_info
          return <ProductCard key={product.product_id} product={{ ...card, short_info: shortInfo }} />
        })}
      </div>
    </div>
  )
}
