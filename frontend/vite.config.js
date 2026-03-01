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
      // Proxy backend API requests to FastAPI server
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
