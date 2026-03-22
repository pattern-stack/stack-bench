---
name: run-and-monitor
description: Start the Stack Bench development environment and monitor application logs. Use when the user asks to start the app, check logs, debug backend/frontend issues, or monitor running services.
allowed-tools: Bash, Read, Grep, Glob
---

# Run & Monitor — Stack Bench Dev Environment

You are an agent responsible for starting the Stack Bench development environment and monitoring its logs.

## Architecture Overview

Stack Bench runs via `pts dev` which starts Docker services + application processes:

**Application processes:**
| Process | Location | Port | Purpose |
|---------|----------|------|---------|
| backend | backend/ | 8500 | FastAPI (uvicorn --reload) |
| frontend | app/frontend/ | 3500 | Vite dev server (React SPA) |

**Docker services:**
| Service | Port | Purpose |
|---------|------|---------|
| postgres | 5932 | PostgreSQL 15 (main database) |

**Port offset:** +500 (configured in `.env`)

## Starting the Environment

### Full startup (recommended)
```bash
pts dev
```
This starts Docker services and application processes. Backend and frontend run in foreground with interleaved logs.

### Services only (database)
```bash
pts services up
```

### Individual apps
```bash
# Backend only
cd backend && uv run uvicorn organisms.api.app:app --reload --port 8500

# Frontend only
cd app/frontend && npm run dev
```

### Database operations
```bash
cd backend && just migrate    # Run alembic migrations
cd backend && just seed       # Seed SDLC agents
```

## Checking Service Status

```bash
pts status                          # Overall status
pts dev status                      # Dev environment status
docker compose ps                   # Docker container health
```

### Verify services are running
```bash
curl http://localhost:8500/health    # Backend health check → {"status": "ok"}
curl http://localhost:3500/          # Frontend Vite dev server
```

### Check ports
```bash
lsof -i :8500    # Backend
lsof -i :3500    # Frontend
lsof -i :5932    # PostgreSQL
```

## Log Monitoring

### Backend logs (uvicorn)
Backend uses Python logging with uvicorn's access log format. When run via `pts dev`, logs stream to stdout.

To capture separately:
```bash
cd backend && uv run uvicorn organisms.api.app:app --reload --port 8500 2>&1 | tee /tmp/sb-backend.log
```

### Frontend logs (Vite)
Vite dev server logs HMR updates and compilation errors. When run via `pts dev`, logs stream to stdout.

To capture separately:
```bash
cd app/frontend && npm run dev 2>&1 | tee /tmp/sb-frontend.log
```

### Docker service logs
```bash
docker compose logs -f postgres     # PostgreSQL logs
docker compose logs --since 5m      # Last 5 minutes
docker compose logs --tail 100      # Last 100 lines
```

## Database Access

```bash
cd backend && just psql             # Interactive psql session (if available)
# Or directly:
psql postgresql://stack-bench:password@localhost:5932/stack-bench
```

## Quality Gates

```bash
pts quality        # Format + lint + typecheck + test (full suite)
pts test           # Tests only
pts format         # Format code
pts lint           # Lint code

# From backend/
cd backend
just test          # Backend tests
just quality       # Backend quality gates
```

## Common Debugging

### Backend won't start
1. Check PostgreSQL: `docker compose ps`
2. Check migrations: `cd backend && just migrate`
3. Check port: `lsof -i :8500`

### Frontend won't start
1. Check deps installed: `cd app/frontend && npm install`
2. Check port: `lsof -i :3500`
3. Check Vite config: `app/frontend/vite.config.ts`

### API proxy not working (frontend → backend)
Check Vite proxy config in `app/frontend/vite.config.ts` — `/api` should proxy to `http://localhost:8500`.

## Stopping Services

```bash
pts stop           # Stop all services and apps
# Or:
pts dev stop       # Stop dev processes
docker compose down  # Stop Docker services
```

## Key Files

| File | Purpose |
|------|---------|
| `.env` | Port configuration, database URL, JWT secret |
| `patterns.yaml` | pts project config (services, apps) |
| `docker-compose.yml` | PostgreSQL service definition |
| `backend/alembic/` | Database migrations |
| `app/frontend/vite.config.ts` | Frontend dev server + API proxy |
