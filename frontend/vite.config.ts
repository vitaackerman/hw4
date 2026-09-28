import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Where /api and /media are forwarded; override with BACKEND_URL if the backend runs elsewhere.
const backend = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Forward API and image requests to the FastAPI backend.
    proxy: {
      '/api': backend,
      '/media': backend,
    },
  },
})
