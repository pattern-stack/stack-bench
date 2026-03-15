---
id: SB-011
title: Go runtime manager (AgentNode + LocalNode)
status: in-progress
epic: EP-002
depends_on: [SB-010]
branch: dugshub/sb-cli-chat/3-runtime-manager
pr: 19
stack: sb-cli-chat
stack_index: 3
created: 2026-03-14
---

# Go Runtime Manager

## Summary

Go-side runtime manager that spawns the Python backend as a subprocess. AgentNode interface designed for multi-agent from day one.

## Scope

What's in:
- `AgentNode` interface: Start, Stop, Health, BaseURL, Name
- `LocalNode`: subprocess uvicorn management
- Auto-start on CLI launch, `--no-backend` flag
- Health indicator in status bar
- Clean shutdown on Ctrl+C

What's out:
- RemoteNode / ContainerNode (interface ready)
- NodePool (deferred)

## Implementation

```
cli/internal/runtime/node.go
cli/internal/runtime/local.go
cli/internal/runtime/manager.go
cli/internal/app/model.go
```

## Verification

- [ ] Auto-starts backend, waits for health
- [ ] Health indicator in status bar
- [ ] `--no-backend` skips auto-start
- [ ] Clean shutdown
- [ ] AgentNode interface extensible

## Notes

GH: #13
