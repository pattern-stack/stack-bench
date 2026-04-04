# Stack Bench

A developer workbench for AI-assisted development with stacked PRs. Combines a Go CLI (TUI), Python backend, and React frontend. Built as a demo application for Pattern Stack.

> **This project is in active development and is not yet functional.** It is shared for visibility into the codebase and workflow — not for use. No license is granted.

## Architecture

- **Backend** — Python (FastAPI, SQLAlchemy, async Postgres) in `app/backend/`
- **CLI** — Go / Bubble Tea TUI in `app/cli/`
- **Frontend** — React in `app/frontend/`
- **Infrastructure** — Terraform (GCP) in `deploy/`

See `docs/adrs/` for architecture decision records.

## Getting Started

### Prerequisites

- [Pattern Stack CLI](https://github.com/pattern-stack/pattern-stack) (`pts`)
- [1Password CLI](https://developer.1password.com/docs/cli/) (`op`) — for secret management
- Docker
- Node.js / Bun
- Go (for CLI development)

### Development

```bash
pts dev          # Start everything (Postgres, Adminer, backend, frontend)
pts db migrate   # Run database migrations
pts db seed      # Seed the database
```

Secrets are resolved natively from 1Password via `patterns.yaml`:

```yaml
secrets:
  backend: 1password
  onepassword:
    vault: DugsApps
    account: my.1password.com
```

No `op run` wrapper needed — `pts dev` resolves `op://` references from `.env.example` at launch and injects them into the environment without writing secrets to disk.

### Useful Commands

| Command | Description |
|---------|-------------|
| `pts dev` | Start full dev environment |
| `pts db migrate` | Run alembic migrations |
| `pts db seed` | Seed database |
| `pts db reset -y` | Drop and recreate all tables |
| `pts secrets check` | Verify all secrets resolve |
| `pts secrets backend` | Show secret backend status |
| `pts doctor` | Health check for dependencies |
