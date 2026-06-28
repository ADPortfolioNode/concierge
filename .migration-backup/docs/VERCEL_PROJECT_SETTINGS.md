Recommended Vercel Project Settings change

1) In the Vercel dashboard, open Project Settings -> General -> Build & Development Settings.
2) Set the `Install Command` to:

   pip install -r requirements.txt && cd frontend && npm ci

3) Set the `Build Command` to:

   npm run build --prefix frontend

4) Set the `Output Directory` to:

   frontend/dist

Notes:
- The `&&` between commands is required so each step runs sequentially in a single shell.
- Alternatively, omit Project Settings and keep `vercel.json` with explicit `builds` + `outputDirectory` to make builds repo-driven and avoid dashboard installCommand issues.
- After updating settings, trigger a new deploy (or push a trivial commit) and verify:
  - GET / -> 200 serving the SPA
  - GET /api/_health -> 200 {"status":"ok"}
