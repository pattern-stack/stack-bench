# ADR-001: CLI/TUI Framework Selection

**Date:** 2026-03-14
**Status:** Accepted
**Deciders:** Dug

## Context

We need a CLI/TUI for the Pattern Stack developer experience. The CLI will be a **thin frontend** that communicates with the Python FastAPI backend over HTTP — it is not responsible for business logic, agent orchestration, or persistence. This architecture means the CLI language does not need to match the backend, freeing us to choose purely on UX quality and long-term viability.

Our reference point is Claude Code (built on Ink/React-for-terminal), which has visual glitches caused by Ink's full-tree re-render architecture. We want to avoid that class of problem.

## Decision

**Bubble Tea v2 (Go)** for the CLI/TUI.

The CLI binary is the user's entry point. On first run, it bootstraps the Python backend (clone, install deps, run migrations, start daemon). After that, it manages the backend lifecycle transparently — starts it if not running, health-checks, restarts if needed. Users never interact with Python directly.

## Options Considered

### Bubble Tea v2 (Go) — Selected

- 40k GitHub stars, backed by Charm (a company), v2 shipped Feb 2026
- v2 "Cursed Renderer" (ncurses-based) with synchronized output eliminates tearing/flicker
- Ecosystem: Glamour (markdown), Lip Gloss (styling), Bubbles (components), Huh (forms)
- Elm Architecture — clean, predictable state management
- `go build` = single static binary, trivial cross-compilation
- Used by NVIDIA, Microsoft, AWS, GitHub in production
- **Streaming markdown gap:** Glamour does full re-render per update, not incremental. Solvable with a custom incremental renderer on Lip Gloss (days of work, not weeks — goldmark AST can be diffed between updates). Considered an acceptable build cost.

### Textual (Python) — Runner-up

- 34k stars, CSS-like styling, best-in-class streaming markdown (v4 "The Streaming Release")
- Same language as backend (but irrelevant — CLI is a thin HTTP client, no shared code)
- **Rejected because:** Single binary distribution is painful (PyInstaller/Nuitka = large, slow startup, fragile). Maintainer on sabbatical with unclear company funding. Distribution matters even if not a hard launch requirement — it affects developer experience for contributors and future users.

### Ratatui (Rust)

- 19k stars, best raw performance (30-40% less memory than Bubble Tea)
- Single binary, excellent rendering
- **Rejected because:** Smaller ecosystem, steeper learning curve, less mature markdown rendering. The performance advantage doesn't matter for a thin HTTP client.

### Ink (TypeScript/React)

- 27k stars, used by Claude Code, Bun compile for distribution
- **Rejected because:** Fundamental architectural flaw — full-tree re-render on every React state change (`eraseLines + rewrite`). This is not a bug, it's how Ink works. It causes the exact visual glitches we're trying to avoid.

### OpenTUI (Zig + TypeScript)

- Powers OpenCode (which migrated away from Bubble Tea v1)
- Zig core with TS/SolidJS/React bindings
- **Rejected because:** v0.1, tiny community, Bun-only, single-company project. Too early to bet on despite being purpose-built for this use case. Worth revisiting in 12 months.

## Architecture

```
User
  │
  ▼
┌─────────────────────────────┐
│  CLI Binary (Go/Bubble Tea) │  ← Single binary, manages backend lifecycle
│  - TUI rendering            │
│  - HTTP client              │
│  - Backend daemon mgmt      │
└──────────┬──────────────────┘
           │ HTTP
           ▼
┌─────────────────────────────┐
│  Backend (Python/FastAPI)   │  ← Bootstrapped + managed by CLI
│  - ConversationService      │
│  - AgentEventBus            │
│  - Runners, Gates, etc.     │
└─────────────────────────────┘
```

The CLI and backend are versioned independently. CLI updates ship as a binary download. Backend updates are triggered by the CLI (`git pull` + `uv sync`).

## Consequences

- **Go dependency:** Team needs Go proficiency for CLI development. Go is straightforward to learn.
- **Incremental markdown renderer:** Must be built on top of Lip Gloss/goldmark. Estimated days, not weeks.
- **Two-language stack:** Go (CLI) + Python (backend). Acceptable because they share no code — the CLI is purely an HTTP client with terminal rendering.
- **Distribution is a strength:** Single binary with zero runtime dependencies. Users install one file.
- **Backend lifecycle management:** CLI must handle starting, health-checking, and restarting the Python backend. Same pattern as Docker Desktop managing its daemon.
