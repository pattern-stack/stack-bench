FROM python:3.13-slim

WORKDIR /app

# Install git (needed for git-based dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY app/backend/pyproject.toml app/backend/uv.lock ./

# Install dependencies (uses GitHub token for private repos)
RUN --mount=type=secret,id=GITHUB_TOKEN \
    GIT_TOKEN=$(cat /run/secrets/GITHUB_TOKEN 2>/dev/null || echo "") && \
    if [ -n "$GIT_TOKEN" ]; then \
        git config --global url."https://${GIT_TOKEN}@github.com/".insteadOf "https://github.com/"; \
    fi && \
    uv sync --frozen --no-dev --no-install-project && \
    git config --global --unset-all url."https://${GIT_TOKEN}@github.com/".insteadOf 2>/dev/null || true

# Copy application code
COPY app/backend/src ./src
COPY app/backend/alembic ./alembic
COPY app/backend/alembic.ini ./
COPY app/backend/entrypoint.sh ./

# Expose port
EXPOSE 8000

# Run migrations then start server
ENV PYTHONPATH=/app/src
CMD ["./entrypoint.sh"]
