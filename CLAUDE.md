# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Stack Bench is a developer workbench for AI-assisted development with stacked PRs. It combines a Go CLI (TUI), a Python backend (pattern-stack + agentic-patterns), and a React frontend.

See `docs/adrs/` for key architecture decisions:
- ADR-001: CLI framework — Go/Bubble Tea
- ADR-002: Backend language — Python/pattern-stack

## Repository Layout

```
backend/          # Python backend (pattern-stack + agentic-patterns)
  features/       # Single-model data services (atoms → features layer)
  molecules/      # Multi-feature business logic
  organisms/      # REST API, CLI (thin interface layer)
  config/         # Settings
  tests/          # pytest suite
docs/
  adrs/           # Architecture Decision Records (append-only, numbered)
  specs/          # Implementation specs (frontmatter status tracking)
    archive/      # Completed/abandoned specs
  epics/          # Groups of related issues (EP-NNN)
  issues/         # Individual work units, 1:1 with branches/PRs (SB-NNN)
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

## Related Repositories

- **agentic-patterns** — Agent framework + backend app (`app/backend/`)
- **backend-patterns** — Pattern Stack framework (EventPattern, BaseService, jobs subsystem)
- **dugshub/stack** — Git stacking tool (source for packages/stack)
