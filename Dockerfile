# Use official lightweight Python image
###
# Multi-stage Dockerfile
# - Optional `frontend` build stage (Node) when ARG BUILD_FRONTEND=1
# - Python runtime image installs either `requirements.txt` or the fuller
#   `requirements.full.txt` when ARG INSTALL_FULL_REQUIREMENTS=1 is passed.
# - Accepts `VITE_API_URL` as a build-arg so frontend builds embed the right
#   API URL at build-time (Vite injects VITE_* envs during build).
###

ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE} AS base

# Prevent Python from writing .pyc files and buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install minimal system dependencies needed to compile native wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*

### Optional frontend build stage (Node) ###############################
ARG BUILD_FRONTEND=0
ARG VITE_API_URL=""
ARG VITE_API_URL_DOCKER=""
FROM node:18-alpine AS frontend-build
WORKDIR /build
# Ensure devDependencies like Vite are installed for the frontend build
ENV NODE_ENV=development
# copy only frontend sources for better cache
COPY frontend/package.json frontend/package-lock.json ./
# Ensure devDependencies like Vite are installed for the frontend build
RUN npm ci --no-audit --no-fund --include=dev
COPY frontend ./
# pass VITE_API_URL or VITE_API_URL_DOCKER as an env var during build so Vite picks it up
ARG VITE_API_URL
ARG VITE_API_URL_DOCKER
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_API_URL_DOCKER=${VITE_API_URL_DOCKER}
RUN if [ -z "$VITE_API_URL" ] && [ -n "$VITE_API_URL_DOCKER" ]; then export VITE_API_URL="$VITE_API_URL_DOCKER"; fi && npm run build --if-present

### Final runtime image ###############################################
FROM base AS runtime

# Build args to control install behavior
ARG INSTALL_FULL_REQUIREMENTS=0

# Copy requirements
COPY requirements.txt ./
COPY requirements.full.txt ./

# Upgrade pip and install requirements; prefer full if requested and present
RUN pip install --upgrade pip
RUN if [ "${INSTALL_FULL_REQUIREMENTS}" = "1" ] && [ -f requirements.full.txt ]; then \
            pip install -r requirements.full.txt ; \
        else \
            pip install -r requirements.txt ; \
        fi

# Copy application code
COPY . .

# Copy built frontend assets from the build stage (if present)
COPY --from=frontend-build /build/dist /app/frontend_dist

# Expose the app port (FastAPI default)
EXPOSE 8000

# Default command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
