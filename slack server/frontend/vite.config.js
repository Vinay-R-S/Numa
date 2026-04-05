import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: ['humblingly-khedival-declan.ngrok-free.dev'],
    proxy: {
      // Proxy API calls to FastAPI backend during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/auth/slack': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/slack': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
