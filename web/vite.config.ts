import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // /api/* → backend (keeps the /api prefix — backend serves /api/*)
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // /sse/* → backend SSE stream
      '/sse': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  worker: {
    format: 'es',
  },
})
