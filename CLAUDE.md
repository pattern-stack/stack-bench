# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Stack Bench is a developer workbench for AI-assisted development with stacked PRs. It combines a Go CLI (TUI), a Python backend (pattern-stack + agentic-patterns), and a React frontend.

See `docs/adrs/` for key architecture decisions:
- ADR-001: CLI framework — Go/Bubble Tea
- ADR-002: Backend language — Python/pattern-stack

## Repository Layout

```
packages/
  stack/        # Git stacking CLI (Clipanion/Bun, being ported to Go)
docs/
  adrs/         # Architecture Decision Records (append-only, numbered)
  specs/        # Implementation specs (frontmatter status tracking)
    archive/    # Completed/abandoned specs
```

## Stack CLI (packages/stack)

```bash
bun run packages/stack/src/cli.ts <command>
# commands: create, status, nav, push, submit, restack, sync
```

## Documentation

Docs follow templates in `docs/adrs/_template.md` and `docs/specs/_template.md`.

- **ADRs:** Numbered, append-only. Status: Draft → Accepted → Superseded.
- **Specs:** Dated, frontmatter-tracked. Status: draft → in-progress → implemented | abandoned.
- Archive completed specs to `docs/specs/archive/`.

## Related Repositories

- **agentic-patterns** — Agent framework + backend app (`app/backend/`)
- **backend-patterns** — Pattern Stack framework (EventPattern, BaseService, jobs subsystem)
- **dugshub/stack** — Git stacking tool (source for packages/stack)
