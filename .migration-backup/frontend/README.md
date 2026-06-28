# Concierge Frontend

This React/TypeScript SPA is a presentation-only shell for the Concierge
backend. It conforms to the architecture outlined in the project specification:

- **React 18** with **Vite**.
- **TypeScript** strict mode.
- **React Router v6** for page navigation.
- **Zustand** global state store.
- **Axios** client with centralized interceptors.  Timeout defaults to 10 000 ms but can be changed
  with the `VITE_API_TIMEOUT` environment variable (useful for slow local servers).
- **ESLint + Prettier** configured for style consistency.
- Absolute imports (`@/` alias) and feature-based folder structure.

## Getting Started

```bash
cd frontend
npm install
npm run dev    # start development server (http://localhost:5173)
```

Build for production:

```bash
npm run build
npm run preview
```

## Architectural Notes

- **No business logic** on the frontend. All decisions are driven by the
  FastAPI response contract.
- API calls go through service modules in `src/api`; components never import
  `axios` directly.
- Global state (conversation, media, confidence, priority, etc.) lives in
  `src/state/appStore.ts` and updates only as a result of API responses.
- Containers fetch and dispatch; presentational components render props only.
- Media rendering is a simple switch-case in `src/components/media/MediaRenderer.tsx`.
- Layout is split into a persistent concierge chat pane and a dynamic
  content area. The chat pane never remounts on route changes.
- Dark theme with matte-black background and subtle red accent (using CSS tokens).
- Spacing system uses 4px units.

## Running Tests / Linting

```bash
npm run lint
```

## File Structure Overview

See the project spec provided by the user; the workspace mirrors that layout.

## Deployment

The app can be served by any static host once built. Ensure the backend
is mounted under `/api/v1/` and CORS is configured accordingly.

### Production environment variables

- Set the `VITE_API_URL` environment variable in your hosting/deployment
  environment to the backend base URL (no trailing slash), for example:

  `VITE_API_URL=https://api.yourdomain.com`

- In Vercel: go to Project → Settings → Environment Variables, add `VITE_API_URL`
  for the `Production` environment and redeploy. The client will throw an
  error at startup if `VITE_API_URL` is missing in production to prevent
  accidentally calling `127.0.0.1:8000` from deployed assets.

---

This repo is intentionally minimal; extend features by adding new containers
and UI/logic in the `features/*` directories. Avoid placing any inference or
strategy logic in the client.
