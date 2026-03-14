/**
 * vite.config.js
 * --------------
 * Vite configuration for the Hebrew Voice Command Reformulation frontend.
 *
 * The dev server proxy forwards all /api/* requests to the FastAPI backend
 * running on port 8000. This avoids CORS issues during development — the
 * browser always talks to the same origin (localhost:5173), and Vite
 * transparently forwards the request to the backend.
 *
 * In the React source code, API calls use the path /api/reformulate rather
 * than http://localhost:8000/reformulate, so no URL changes are needed when
 * deploying to a production environment that co-hosts the frontend and backend.
 */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy /api/* → http://localhost:8000/*
      // e.g. /api/reformulate → http://localhost:8000/reformulate
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
