---
title: Command Orchestrator
date: 2026-03-21
status: draft
branch:
depends_on: []
adrs: [001, 004]
---

# Command Orchestrator

## Goal

Define a semantic abstraction — the **command orchestrator** — that every CLI command path plugs into. Instead of each command building bespoke screens and interactions, the orchestrator provides a consistent skeleton: dashboard view, quick commands, detail drill-down, and action dispatch. We build this scaffold first so that every new command surface we add downstream is structurally clean from day one.

This is the TUI equivalent of a resource controller pattern. The orchestrator knows the *shape* of every command surface and provides the consistent structure; individual commands fill in the domain-specific content.

## The Idea

Every command path in `sb` (stacks, streams, projects, branches, etc.) shares the same interaction surface:

```
┌─────────────────────────────────────────┐
│  Dashboard View                         │  ← default landing for this resource
│  - summary / list / status at a glance  │
│  - contextual to current state          │
├─────────────────────────────────────────┤
│  Quick Commands                         │  ← 2-3 most common actions, always visible
│  - create, open, push, submit, etc.     │
│  - resource-specific but structurally   │
│    consistent                           │
├─────────────────────────────────────────┤
│  Detail View                            │  ← drill into a specific entity
│  - full entity detail                   │
│  - sub-resource navigation              │
├─────────────────────────────────────────┤
│  Action Palette                         │  ← all available operations
│  - contextual to selected entity/state  │
│  - lifecycle-aware (only valid actions) │
└─────────────────────────────────────────┘
```

The orchestrator manages:
- **Registration** — each command path declares its dashboard, quick commands, detail view, and actions
- **Navigation** — consistent patterns for moving between dashboard ↔ detail ↔ action
- **State** — what's selected, what's active, what actions are valid right now
- **Rendering** — the structural skeleton (layout, chrome, transitions) is owned by the orchestrator; content is owned by the command

## Why Build This First

Without the orchestrator, each new command surface is a greenfield design exercise. With it:
- Adding a new resource (e.g. `sb workspaces`) is "implement 4 interfaces" not "design a screen"
- Consistency is structural, not cosmetic — navigation, keybindings, layout all come for free
- The TUI prototype (3-tab layout) proved the interaction model works; now we need the abstraction beneath it

## Command Surfaces (Initial)

| Path | Dashboard | Quick Commands | Detail |
|------|-----------|----------------|--------|
| stacks | stack list + status | create, push, submit | stack detail → branch list |
| streams | task session overview | - | session → agent → messages |
| projects | project list + active state | create, archive | project detail → workspaces |
| chat | conversation timeline | new, recall | message thread |

## Open Questions

1. **Where does this live?** Go types in the CLI? Or does the backend need to know about command surfaces too (e.g. for the web UI)?
2. **How deep does the skeleton go?** Just layout + navigation? Or also keybindings, help text, accessibility?
3. **Relationship to the existing command registry** (`cli/internal/command/`) — does the orchestrator replace it, wrap it, or sit alongside?
4. **Does the orchestrator also handle the REST API routes?** Same resource pattern for backend endpoints, or CLI-only abstraction?
5. **Terminal layer integration** — does the orchestrator manage the slide-up terminal panel context binding, or is that separate?
