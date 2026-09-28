import { useState } from 'react'
import { cutoutUrl } from '../api'

type Props = {
  src: string
  alt: string
  loading?: 'lazy' | 'eager'
  className?: string
}

// Shows the garment cut out of its black/white photo backdrop; falls back to the original photo
// if the backend has no clean cutout for it (e.g. shadows as dark as the backdrop).
export default function ProductImage({ src, alt, loading = 'lazy', className = '' }: Props) {
  const [failedFor, setFailedFor] = useState<string | null>(null)
  const failed = failedFor === src
  return (
    <img
      src={failed ? src : cutoutUrl(src)}
      alt={alt}
      loading={loading}
      draggable={false}
      className={`${className} ${failed ? 'is-photo' : 'is-cutout'}`.trim()}
      onError={() => setFailedFor(src)}
    />
  )
}
