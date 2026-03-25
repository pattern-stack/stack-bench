# Stack Bench

A developer workbench for AI-assisted development with stacked PRs. Combines a Go CLI (TUI), Python backend, and React frontend. Built as a demo application for Pattern Stack.

> **This project is in active development and is not yet functional.** It is shared for visibility into the codebase and workflow — not for use. No license is granted.

## Architecture

- **Backend** — Python (FastAPI, SQLAlchemy, async Postgres) in `app/backend/`
- **CLI** — Go / Bubble Tea TUI in `app/cli/`
- **Frontend** — React in `app/frontend/`
- **Infrastructure** — Terraform (GCP) in `deploy/`

See `docs/adrs/` for architecture decision records.
