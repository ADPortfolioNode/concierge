import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const backendTarget = process.env.BACKEND_URL ?? (process.env.IN_DOCKER === 'true' ? 'http://app:8000' : 'http://localhost:8001')

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
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
