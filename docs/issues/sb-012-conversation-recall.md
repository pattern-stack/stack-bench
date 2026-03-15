---
id: SB-012
title: Conversation recall, restore, and branch
status: in-progress
epic: EP-002
depends_on: [SB-011]
branch: dugshub/sb-cli-chat/4-conversation-recall
pr: 20
stack: sb-cli-chat
stack_index: 4
created: 2026-03-14
---

# Conversation Recall

## Summary

List past conversations, restore/continue them, and branch from any point in history. DB schema already has `branched_from_id` and `branched_at_sequence`.

## Scope

What's in:
- Backend: list with filters, branch endpoint
- CLI: conversation picker (new / continue / branch)
- CLI: conversation metadata display

What's out:
- Content search within conversations
- Export/import
- Sharing

## Implementation

```
backend/organisms/api/routers/conversations.py
backend/molecules/entities/conversation_entity.py
backend/molecules/apis/conversation_api.py
cli/internal/chat/picker.go
cli/internal/api/client.go
```

## Verification

- [ ] List with filters works
- [ ] Branch creates forked conversation with history
- [ ] CLI picker shows conversations
- [ ] Continue loads history and resumes
- [ ] `pts test` passes

## Notes

GH: #14
