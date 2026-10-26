import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // /api/* → backend (keeps /api prefix — backend serves /api/*)
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.error('[proxy] /api error:', err.message);
          });
        },
      },
      // /sse/* → backend SSE stream
      '/sse': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.error('[proxy] /sse error:', err.message);
          });
        },
      },
    },
  },
  worker: {
    format: 'es',
  },
})
