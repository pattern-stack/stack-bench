---
id: SB-063
title: Port service lifecycle from main
status: draft
epic: EP-017
depends_on: [SB-059]
branch:
pr:
stack: agentic-tui
stack_index: 6
created: 2026-04-09
---

# Port service lifecycle from main

## Summary

Update `internal/service/` to match main's version: rename `LocalService` to
`ExecService` and incorporate any polish fixes. This is the smallest issue in
the epic — the service abstraction is nearly identical between branches.

## Scope

What's in:
- Rename `LocalService` → `ExecService` (if PR #198 still uses the old name)
- Verify `ServiceManager` matches main's version
- Verify `ServiceNode` interface is identical
- Update imports to `internal/types` if needed

What's out:
- Public `ServiceNode` type alias (SB-060)
- New service implementations

## Implementation

Source: `packages/agent-tui/internal/service/`

```
packages/agentic-tui/internal/service/
  node.go       ← ServiceNode interface, ServiceStatus enum
  local.go      ← ExecService (renamed from LocalService)
  manager.go    ← ServiceManager
```

The `ExecService`:
- Spawns backend via `exec.Command` with custom Env, Dir
- Health checks via HTTP GET to configurable path (default `/health`)
- Polls every 200ms, 30s timeout
- Graceful shutdown: 5s grace → SIGKILL
- Process group tracking for clean shutdown

Compare PR #198's `service/` with main's and take the superset.

## Verification

- [ ] `go build ./internal/service/...` passes
- [ ] `ServiceNode` interface matches main's version
- [ ] `ExecService` (not `LocalService`) is the exported name
- [ ] `ServiceManager.StartAll/StopAll/HealthSummary` methods exist

## Notes

- This is likely a very small diff — possibly just a rename
- Check if PR #198 already uses `ExecService` name
