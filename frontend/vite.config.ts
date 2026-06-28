import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Pin the dev server to a stable port so the origin matches the backend
    // CORS allowlist. strictPort makes Vite fail loudly instead of silently
    // drifting to 5174/5175 (which would re-trigger CORS errors).
    port: 5173,
    strictPort: true,
  },
})
