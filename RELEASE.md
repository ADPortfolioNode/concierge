# Release 1.0.0

This document describes the production-ready architecture, deployment
recommendations, and important conventions for the v1.0 release of
Concierge.

## Architecture Overview

- **core/**: shared low-level utilities and primitives such as the
  asynchronous concurrency manager. This package contains code with
  minimal external dependencies and no knowledge of orchestration
  policies.

- **orchestration/**: contains higher-level coordination logic, most
  notably the `SacredTimeline` orchestrator and the distributed helper
  modules. These components rely on `core` primitives but do not depend
  on application-specific endpoints or configuration.

- **app.py**: FastAPI front-end exposing the `/ask` endpoint, health
  checks, and configuration.  Imports orchestration components and
  wires them together.

- **tests/**: integration and unit tests, updated to import from the
  new package hierarchy.

- **frontend/**: React/Vite single-page app with end-to-end Playwright
  tests.  The front-end communicates with the backend via Axios and
  handles API key auth when running in SaaS mode.

- Dockerfile and `docker-compose.yml` provide a convenient local
  development environment including vector stores (Chroma or Qdrant).

## Release Preparation Checklist

1. Bump `VERSION` file to the new semantic version (`1.0.0`).
2. Update health endpoints to report the version (already implemented in
   `app.py`).
3. Ensure all imports refer to the structured packages (`core`,
   `orchestration`) or use compatibility shims in the workspace root.
4. Run the full test suite:
   - `pytest` for Python tests
   - `npm run test` or `npx playwright test` for front-end e2e checks
5. Build Docker images and run `docker-compose up --build` to verify the
   containerized stack starts correctly.
6. Audit the changelog and update `README.md` with any new runtime
   requirements or environment variables (e.g. `BACKEND_TIMEOUT`,
   `API_KEY_HEADER`).
7. Tag the release in git: `git tag -a v1.0.0 -m "Release v1.0.0"` and
   push the tag.
8. Update deployment scripts or CI pipelines to use the new version and
   optional multi-tenant features.

## Post-release

- Monitor `/health/system` for uptime, thread count, memory status, and
  vector store connectivity.
- Review usage logs for API key activity and enforce rate limits as
  required by the SaaS plan.
- Document any hotfix procedure in this file.

---

Thank you for helping make Concierge 1.0 a reality!