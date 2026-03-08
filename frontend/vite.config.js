import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: false,
    proxy: {
      // Proxy backend API requests to FastAPI server (frontend uses relative URLs in dev)
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
      '/brain': { target: 'http://localhost:8000', changeOrigin: true },
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/voice': { target: 'http://localhost:8000', changeOrigin: true },
      '/chats': { target: 'http://localhost:8000', changeOrigin: true },
      '/retrieve': { target: 'http://localhost:8000', changeOrigin: true },
      '/knowledge-base': { target: 'http://localhost:8000', changeOrigin: true },
      '/repositories': { target: 'http://localhost:8000', changeOrigin: true },
      '/kpi': { target: 'http://localhost:8000', changeOrigin: true },
      '/scrape': { target: 'http://localhost:8000', changeOrigin: true },
      '/autonomous-learning': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/proactive-learning': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/training': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/learning-memory': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/documents': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/genesis': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    }
  }
})
