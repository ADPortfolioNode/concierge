# Concierge Docker Distribution

This repository supports a self-contained Docker distribution for local use.

## How to use

1. Unzip the distribution package.
2. Open a terminal in the project root.
3. Run:

   ```bash
   docker compose up --build
   ```

4. Open the frontend in your browser:

   ```
   http://localhost:5173
   ```

5. To stop and remove containers and volumes:

   ```bash
   docker compose down -v
   ```

## Notes

- Backend is exposed on `http://localhost:8001`.
- Frontend is exposed on `http://localhost:5173`.
- Persistent Chroma memory is stored in the `chroma_data` Docker volume.
- The frontend is configured to use `VITE_BACKEND_URL` in Docker.
- This distribution does not require Vercel or ngrok.
