# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Stack Bench is a developer workbench for AI-assisted development with stacked PRs. It combines a Go CLI (TUI), a Python backend (pattern-stack + agentic-patterns), and a React frontend.

See `docs/adrs/` for key architecture decisions:
- ADR-001: CLI framework — Go/Bubble Tea
- ADR-002: Backend language — Python/pattern-stack

## Repository Layout

```
app/
  backend/              # Python backend (self-contained service)
    src/                # Source code (PYTHONPATH root)
      features/         # Single-model data services (atoms → features layer)
      molecules/        # Multi-feature business logic
      organisms/        # REST API, CLI (thin interface layer)
      config/           # Settings
      seeds/            # Database seeding specifications
    __tests__/          # pytest suite
    alembic/            # Database migrations
    pyproject.toml      # Python project config
    Justfile            # Backend-specific commands
  cli/                  # Go CLI (Bubble Tea TUI)
    Justfile            # CLI-specific commands
  frontend/             # React frontend (planned)
docs/
  adrs/                 # Architecture Decision Records (append-only, numbered)
  specs/                # Implementation specs (frontmatter status tracking)
    archive/            # Completed/abandoned specs
  epics/                # Groups of related issues (EP-NNN)
  issues/               # Individual work units, 1:1 with branches/PRs (SB-NNN)
```

## Stack CLI

```bash
stack <command>
# commands: create, status, nav, push, submit, restack, sync
```

Installed globally via Bun. State stored in `~/.claude/stacks/`.
Branch naming: `user/stack-name/index-description` (e.g. `dug/sb-backend/1-bootstrap`).

## Documentation

Docs follow templates in `docs/{adrs,specs,epics,issues}/_template.md`.

- **ADRs:** Numbered, append-only. Status: Draft → Accepted → Superseded.
- **Specs:** Dated, frontmatter-tracked. Status: draft → in-progress → implemented | abandoned.
- **Epics:** Numbered (EP-NNN). Groups of related issues. Status: planning → active → completed.
- **Issues:** Numbered (SB-NNN). 1:1 with branches/PRs. Frontmatter tracks epic, depends_on, stack, stack_index.
- Archive completed specs to `docs/specs/archive/`.

## Backend Development

```bash
# pts commands (from project root)
pts dev           # Start backend + frontend + Postgres
pts services up   # Start Postgres only
pts test          # Run pytest
pts quality       # Format + lint + typecheck + test

# just commands (from app/backend/)
cd app/backend
just test         # Run tests
just quality      # Format + lint + typecheck + test
just migrate      # Run alembic migrations
just seed         # Seed database with SDLC agents

# Root Justfile (from project root)
just test         # Run all tests (backend + CLI)
just quality      # Run all quality gates
just migrate      # Run backend migrations
just seed         # Seed database
```

## AI Workflow Config

See `.claude/sdlc.yml` for SDLC primitive configuration (language, framework, quality gates, task management).

## Related Repositories

- **agentic-patterns** — Agent framework + backend app (`app/backend/`)
- **backend-patterns** — Pattern Stack framework (EventPattern, BaseService, jobs subsystem)
- **dugshub/stack** — Git stacking tool (source for packages/stack)
