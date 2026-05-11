# Concierge AI — Mobile

Expo React Native companion app for Concierge AI. Connects to the same Python FastAPI backend as the web app.

## Screens

| Tab | Description |
|-----|-------------|
| **Chat** | AI chat with animated message bubbles, typing indicator, haptic feedback on send |
| **Tasks** | Live task monitor — polls `/api/v1/tasks` every 8 s, pull-to-refresh, colour-coded status badges |

## Getting started

```bash
# From the workspace root
pnpm --filter @workspace/concierge-mobile run dev
```

Then open Expo Go on your phone and scan the QR code, or press `w` for the browser preview.

## Environment

| Variable | Description |
|----------|-------------|
| `EXPO_PUBLIC_DOMAIN` | Backend domain (e.g. `abc123.replit.dev`). Set automatically in Replit. |

The app calls `setApiBaseUrl()` in `app/_layout.tsx` at boot using this value.

## Key files

```
app/
  _layout.tsx          Root layout — sets API base URL, loads fonts
  (tabs)/
    _layout.tsx        2-tab navigator (Chat, Tasks)
    index.tsx          Chat screen
    tasks.tsx          Task monitor screen
constants/
  colors.ts            Brand colour tokens (mirrors web app palette)
lib/
  api.ts               Typed API client — ApiEnvelope<T> parsing
assets/
  images/
    icon.png           App icon (constellation on navy #0F172A)
```

## API contract

All responses are wrapped in `ApiEnvelope<T>`:

```json
{
  "status": "success",
  "data": { ... },
  "timestamp": "...",
  "request_id": "..."
}
```

- `POST /api/v1/concierge/message` — send a chat message, returns `data.content`
- `GET /api/v1/tasks` — list all tasks, returns `data` array
- `GET /api/v1/tasks/:id` — single task tree, returns `data`

## Design tokens

Colours match the web app's light theme:

| Token | Value |
|-------|-------|
| Navy (background) | `#0F172A` |
| Blue (accent) | `#2563EB` |
| Light blue | `#38BDF8` |
| Surface | `#F0F8FF` |
| Text primary | `#0F172A` |
| Text muted | `#64748B` |

Font: Inter (Regular 400, Medium 500, SemiBold 600, Bold 700).
