export type SizeStock = {
  size: string
  quantity: number
}

export type Product = {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  price: number
  image_url: string
  // False when there's no clean transparent cutout (the site falls back to the photo).
  has_cutout: boolean
  inventory: SizeStock[]
  total_stock: number
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(response.status === 404 ? 'not-found' : `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const fetchProducts = () => getJson<Product[]>('/api/products')
export const fetchProduct = (id: string) => getJson<Product>(`/api/products/${encodeURIComponent(id)}`)

// Transparent garment cutout served by the backend (cutouts.py); 404 means "use the original photo".
export const cutoutUrl = (imageUrl: string) =>
  imageUrl.replace('/media/products/', '/media/cutouts/').replace(/\.[a-z0-9]+$/i, '.webp')

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

// garment_type in the database is free text (22 variants), so group it into shop categories.
export const CATEGORIES = ['Hoodies', 'Crewnecks', 'Tees', 'Quarter-zips', 'Jackets & fleece'] as const
export type Category = (typeof CATEGORIES)[number]

export function categoryOf(garmentType: string): Category {
  const type = garmentType.toLowerCase()
  if (type.includes('quarter-zip')) return 'Quarter-zips'
  if (type.includes('hood')) return 'Hoodies'
  if (type.includes('jacket') || type.includes('fleece')) return 'Jackets & fleece'
  if (type.includes('crew') && !type.includes('t-shirt')) return 'Crewnecks'
  if (type.includes('mockneck')) return 'Crewnecks'
  return 'Tees'
}

// What a product card needs; catalogue products and chat matches both map to this.
export type CardData = {
  product_id: string
  name: string
  price: number
  image_url: string
  short_info: string
  total_stock: number
  // Per-size stock when known (catalogue products); chat matches only have the total.
  sizes?: SizeStock[]
}

export const cardFromProduct = (product: Product): CardData => ({
  product_id: product.product_id,
  name: product.name,
  price: product.price,
  image_url: product.image_url,
  short_info: shortDescription(product.description),
  total_stock: product.total_stock,
  sizes: product.inventory,
})

export function shortDescription(description: string, maxLength = 96): string {
  const firstSentence = description.split(/(?<=\.)\s/)[0]
  const text = firstSentence.length <= maxLength ? firstSentence : description
  return text.length <= maxLength ? text : `${text.slice(0, maxLength).replace(/\s+\S*$/, '')}…`
}

// Matches backend PublicUser: never includes the password hash or salt.
export type User = {
  id: number
  first_name: string
  last_name: string
  name: string
  email: string
  created_at: string
}

export type RegisterInput = { first_name: string; last_name: string; email: string; password: string }
export type LoginInput = { email: string; password: string }

// Thrown when the backend rejects the session token, so the UI can log the user out.
export class SessionExpiredError extends Error {}

async function requestJson<T>(url: string, init: { method: 'GET' | 'POST'; body?: unknown; token?: string | null }): Promise<T> {
  const headers: Record<string, string> = {}
  if (init.body !== undefined) headers['Content-Type'] = 'application/json'
  if (init.token) headers.Authorization = `Bearer ${init.token}`
  let response: Response
  try {
    response = await fetch(url, {
      method: init.method,
      headers,
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    })
  } catch {
    throw new Error("Can't reach the server. Is the backend running?")
  }
  const data = await response.json().catch(() => null)
  if (response.status === 401 && init.token) {
    throw new SessionExpiredError(data?.detail ?? 'Your session has expired. Please log in again.')
  }
  if (!response.ok) {
    const detail = data?.detail
    if (typeof detail === 'string' && detail !== 'Not Found') throw new Error(detail)
    // 404 = backend running old code without this route; 5xx without a message = Vite proxy can't reach the backend.
    if (response.status === 404 || response.status >= 500) {
      throw new Error("Can't reach the server. Make sure the backend is running the latest code.")
    }
    throw new Error('Something went wrong. Please try again.')
  }
  return data as T
}

// Matches backend auth.AuthResponse.
export type AuthResponse = { user: User; token: string }

export const registerUser = (input: RegisterInput) =>
  requestJson<AuthResponse>('/api/auth/register', { method: 'POST', body: input })
export const loginUser = (input: LoginInput) => requestJson<AuthResponse>('/api/auth/login', { method: 'POST', body: input })

export type ChatTurn = { role: 'user' | 'assistant'; content: string }

// Matches backend models.ProductCard: built from the database, not from model text.
export type ChatProductCard = {
  product_id: string
  name: string
  price: number
  image_url: string
  total_stock: number
}

// Matches backend models.ProductMatch / ChatSearchResults: every product the agent's search matched.
export type ProductMatch = {
  product_id: string
  name: string
  garment_type: string
  price: number
  image_url: string
  short_description: string
  colors: string[]
  total_stock: number
}

export type ChatSearchResults = { query: string; total_matches: number; products: ProductMatch[] }

// Matches backend models.ChatReply.
export type ChatReply = {
  reply: string
  products: ChatProductCard[]
  search_results: ChatSearchResults | null
  // Set when the agent is asking "which one do you mean?"; shown as tap-to-choose buttons.
  clarification_options: ChatProductCard[]
}

// Matches backend models.PageContext: only ids and fixed labels, the backend looks up names itself.
export type PageKind = 'home' | 'products' | 'product' | 'about' | 'login' | 'create-account' | 'other'
export type PageContext = { kind: PageKind; product_id?: string; category?: string }

// Matches backend models.HistoryMessage.
export type HistoryMessage = {
  id: number
  role: 'user' | 'assistant'
  content: string
  products: ChatProductCard[]
  created_at: string
}

export const sendChat = (message: string, history: ChatTurn[], page: PageContext, token: string | null) =>
  requestJson<ChatReply>('/api/chat', { method: 'POST', body: { message, history, page }, token })

export const fetchChatHistory = (token: string) =>
  requestJson<{ messages: HistoryMessage[] }>('/api/chat/history', { method: 'GET', token })
