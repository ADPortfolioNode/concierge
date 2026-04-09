import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Prefer explicit BACKEND_URL (or VITE_API_URL) for proxy target; fall back
// to Docker service name when running inside container, otherwise localhost
// is only used as a last-resort for local development.
const backendTarget = process.env.BACKEND_URL ?? process.env.VITE_API_URL ?? (process.env.IN_DOCKER === 'true' ? 'http://app:8000' : 'http://localhost:8001')
const basePath = process.env.VITE_BASE_URL ?? '/'

export default defineConfig({
  base: basePath,
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src'), react: path.resolve(__dirname, 'node_modules/react'), 'react-dom': path.resolve(__dirname, 'node_modules/react-dom') } },
  server: {
    port: 5173, host: true,
    proxy: {
      '/api/v1': {
        target: backendTarget, changeOrigin: true, secure: false,
        configure(proxy) {
          proxy.on('error', (_err, _req, res) => {
            try { if (!res.headersSent) { res.writeHead(503, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ status: 'error', message: 'Backend unavailable.' })); } } catch {}
          });
        },
      },
    },
  },
});
