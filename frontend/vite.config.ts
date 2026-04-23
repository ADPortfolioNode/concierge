import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Prefer explicit BACKEND_URL (or VITE_API_URL) for proxy target; fall back
// to Docker service name when running inside container, otherwise localhost
// is only used as a last-resort for local development.
// NOTE: frontend runtime also reads BACKEND_URL as a VITE_API_URL alias so
// the dev proxy and client request URL are consistent.
const getEnv = (key: string) => (process.env[key] || '').replace(/\/$/, '');
const VITE_BACKEND_URL = getEnv('VITE_BACKEND_URL');
const VITE_API_URL = getEnv('VITE_API_URL') || VITE_BACKEND_URL || getEnv('BACKEND_URL');
const VITE_API_URL_LOCAL = getEnv('VITE_API_URL_LOCAL');
const VITE_API_URL_DOCKER = getEnv('VITE_API_URL_DOCKER');
const VITE_API_URL_STAGING = getEnv('VITE_API_URL_STAGING');
const VITE_API_URL_PRODUCTION = getEnv('VITE_API_URL_PRODUCTION');
const VITE_API_URL_SET = (process.env.VITE_API_URL_SET || process.env.VITE_API_SERVER_SET || '').trim().toLowerCase();
const VITE_API_URL_AUTO_DETECT = (process.env.VITE_API_URL_AUTO_DETECT || 'true').toLowerCase() !== 'false';
const MODE = (process.env.MODE || process.env.NODE_ENV || '').toLowerCase() || 'development';

const SERVER_URLS: Record<string, string> = {
  // Local dev should prefer the helper-script managed backend on 8001.
  local: VITE_API_URL_LOCAL || VITE_API_URL || 'http://127.0.0.1:8001',
  docker: VITE_API_URL_DOCKER || VITE_API_URL || 'http://app:8001',
  staging: VITE_API_URL_STAGING || VITE_API_URL || '',
  production: VITE_API_URL_PRODUCTION || VITE_API_URL || '',
  auto: VITE_API_URL || '',
};

const backendTarget = (() => {
  const isLocalDev = process.env.DEV === 'true' || MODE === 'development';
  if (isLocalDev) {
    return process.env.IN_DOCKER === 'true' ? SERVER_URLS.docker : SERVER_URLS.local;
  }
  if (VITE_API_URL_SET) {
    return SERVER_URLS[VITE_API_URL_SET] || SERVER_URLS.local;
  }
  if (!VITE_API_URL_AUTO_DETECT) {
    return process.env.IN_DOCKER === 'true' ? SERVER_URLS.docker : SERVER_URLS.local;
  }
  return process.env.IN_DOCKER === 'true' ? SERVER_URLS.docker : SERVER_URLS.local;
})();
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
      '/media': {
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
