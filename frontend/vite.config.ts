import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    // allow connections from outside the container (required when running in
    // Docker).  Without this the dev server binds to localhost only and the
    // host machine cannot reach it, leading to a blank page when you visit
    // http://localhost:5173 in your browser.
    host: true,
    proxy: {
      // proxy frontend API calls to backend during development
      // proxy frontend API calls to backend during development
      // use BACKEND_URL env var when provided; when running inside Docker
      // the frontend container can reach the backend at the compose
      // service hostname `app:8000` so we fall back to that when
      // `IN_DOCKER=true` is set in the container environment.
      '/api/v1': {
        target: process.env.BACKEND_URL || (process.env.IN_DOCKER === 'true' ? 'http://app:8000' : 'http://localhost:8001'),
        changeOrigin: true,
        secure: false,
      },
    },
  },
});