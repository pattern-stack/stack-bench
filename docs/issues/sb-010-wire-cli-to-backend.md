---
id: SB-010
title: Wire CLI chat to backend (HTTP client + SSE parser)
status: in-progress
epic: EP-002
depends_on: [SB-008, SB-009]
branch: dugshub/sb-cli-chat/2-wire-cli-to-backend
pr: 18
stack: sb-cli-chat
stack_index: 2
created: 2026-03-14
---

# Wire CLI to Backend

## Summary

Diamond merge point. Connect Go chat UI to Python backend with HTTP client + SSE parser. End-to-end: launch CLI → pick agent → chat with Claude.

## Scope

What's in:
- Go HTTP client for REST API
- SSE parser (handle known events, ignore unknown)
- Wire chat model to real API
- End-to-end working chat

What's out:
- Auto-starting backend (SB-011)
- Conversation recall (SB-012)

## Implementation

```
cli/internal/api/client.go
cli/internal/api/sse.go
cli/internal/api/types.go
cli/internal/chat/model.go
cli/internal/chat/update.go
```

## Verification

- [ ] Creates conversation via API
- [ ] Sends message, receives SSE stream
- [ ] Real-time rendering of thinking/text/tools
- [ ] Unknown events silently ignored

## Notes

GH: #12
