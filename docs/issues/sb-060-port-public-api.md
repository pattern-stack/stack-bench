---
id: SB-060
title: Port public API layer from main
status: draft
epic: EP-017
depends_on: [SB-059]
branch: dug/agentic-tui/3-public-api
pr:
stack: agentic-tui
stack_index: 3
created: 2026-04-09
---

# Port public API layer from main

## Summary

Add the public API surface that consumers use to configure and run the TUI.
Adapted from main's `packages/agent-tui/{tui.go,client.go,config.go,...}` but
simplified — no adapter boilerplate since types are now unified (SB-059).

## Scope

What's in:
- `tui.go` — `App` struct, `New(Config)`, `Run()`, `RunGallery()`
- `client.go` — `NewHTTPClient()`, `NewStdioClient()`, `NewStubClient()` factories
- `config.go` — `Config`, `EndpointConfig`, `CommandDef`
- `service.go` — `ServiceNode` type alias
- `stdio.go` — `StdioConfig` struct
- `theme.go` — `Theme` type alias
- Reconcile `app.New()` signature: adopt main's `(client, mgr, reg, cfg)` pattern but keep PR #198's model fields (demo, gallery, statusSpinner)
- Delete `internal_bridge.go` if it exists (no longer needed)

What's out:
- `publicClientAdapter` / `internalClientAdapter` — eliminated by type unification
- Transport implementations (SB-061, SB-062)
- Service lifecycle details (SB-063)

## Implementation

Source: `packages/agent-tui/{tui.go,client.go,config.go,command.go,service.go,stdio.go,theme.go}`

Key adaptations from main:
- `App.resolveBackend()` works as-is once adapters are removed
- `App.buildRegistry()` for consumer commands works as-is
- `App.Run()` — service start, signal handling, Bubble Tea program creation
- Transport factories return `types.Client` directly (no wrapping)

Reconcile `internal/app/model.go`:
- Adopt main's constructor: `New(client types.Client, mgr *service.ServiceManager, reg *command.Registry, cfg Config) Model`
- Add `Config` struct: `AppName string`, `AssistantLabel string`
- Keep PR #198's model fields: `demo bool`, `demoRunner *DemoRunner`, `gallery bool`, `statusSpinner atoms.Spinner`
- Keep PR #198's height calculation (`m.height - 5`, accounts for richer chrome)
- Pass `cfg.AssistantLabel` to `chat.New()`

```
packages/agentic-tui/
  tui.go          ← App, New, Run, RunGallery
  client.go       ← NewHTTPClient, NewStdioClient, NewStubClient (thin factories)
  config.go       ← Config, EndpointConfig, CommandDef
  types.go        ← re-exports from internal/types (already created in SB-059)
  service.go      ← type ServiceNode = service.ServiceNode
  stdio.go        ← StdioConfig struct
  theme.go        ← type Theme = theme.Theme
```

## Verification

- [ ] `go build ./...` passes
- [ ] A minimal consumer program can `tui.New(cfg)` and `app.Run()` compiles
- [ ] `Config` supports all three backend modes: `BackendURL`, `BackendService`, `BackendStdio`
- [ ] `Config.Commands` allows registering custom slash commands
- [ ] No `publicClientAdapter` or `internalClientAdapter` in the codebase

## Notes

- Source for main's public API: `packages/agent-tui/tui.go` (166 lines), `client.go` (149 lines), `config.go` (42 lines)
- The `OnReady` callback in main's Config is optional — include it if present, skip if not
