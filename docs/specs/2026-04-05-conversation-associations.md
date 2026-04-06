---
title: Conversation Associations via RelationalPattern
status: in-progress
created: 2026-04-05
epic: EP-016
depends_on: [ADR-005]
---

# Conversation Associations

## Goal

Wire conversations to tasks, projects, stacks, and epics using pattern-stack's RelationalPattern. This enables the workspace detail view to load real conversation data for a task, and unblocks the future planning interface.

## Context

**ADR-005** decided on RelationalPattern for polymorphic conversation-entity links. The Conversation model already exists with messages, SSE streaming, and state machine. The workspace detail currently renders demo chat data. This spec wires real data.

### What exists

- `Conversation` model (EventPattern) — `features/conversations/models.py`
- `Message` model — `features/conversations/` (has parts: text, thinking, toolCall, error)
- `ConversationAPI` molecule — `molecules/apis/conversation_api.py`
- `ConversationRunner` — `molecules/runtime/conversation_runner.py` (SSE streaming)
- `ChatRoom` organism — frontend component with `useEventSource` + `useChatMessages`
- `RelationalPattern` — available in pattern-stack atoms

### What's missing

1. `conversation_type` field on Conversation model
2. RelationalPattern instance for conversation links (or reuse generic)
3. API endpoint to get conversation for a task
4. Frontend hook to fetch conversation by entity
5. Wiring WorkspaceDetailPage to real ChatRoom instead of demo data

## Plan

### Step 1: Add conversation_type to Conversation model

- **Files**: `features/conversations/models.py`, new Alembic migration
- **Changes**: Add `conversation_type = Field(str, default="execution", choices=["planning", "execution", "review"])`
- **Why**: Quick filter for conversation purpose without joining RelationalPattern

### Step 2: Create ConversationLink model

- **Files**: New `features/conversations/models.py` (add to existing file)
- **Changes**: Create a thin wrapper around RelationalPattern or use it directly:

```python
class ConversationLink(RelationalPattern):
    __tablename__ = "conversation_links"

    class Pattern:
        entity = "conversation_link"
        reference_prefix = "CL"
```

Or skip the subclass and use RelationalPattern directly with `entity_a_type="conversation"`.

- **Decision**: Use RelationalPattern directly — no subclass needed unless we want custom methods. The `relationship_type` field handles "planning", "execution", "review", "produced".
- **Why**: Leverages existing framework. No new models to maintain.

### Step 3: API endpoint — get conversation for entity

- **Files**: `organisms/api/routers/conversations.py`
- **Changes**: Add endpoint:
  - `GET /conversations/by-entity?entity_type=task&entity_id={id}&role=execution`
  - Returns the active conversation (with messages) linked to that entity
  - Creates one if none exists (for execution conversations)
- **Why**: Frontend needs to discover which conversation belongs to a workspace

### Step 4: Link conversations on task execution

- **Files**: `molecules/apis/task_api.py` or a new `ConversationLinkService`
- **Changes**: When a Job starts for a Task, create a Conversation and link it:
  ```python
  conv = await conversation_service.create(db, ConversationCreate(
      agent_name="orchestrator",
      conversation_type="execution",
      project_id=task.project_id,
  ))
  # Link conversation → task
  await RelationalPattern.create(db, entity_a_type="conversation", entity_a_id=conv.id,
      entity_b_type="task", entity_b_id=task.id, relationship_type="execution")
  ```
- **Why**: Ensures every task execution has a traceable conversation

### Step 5: Frontend — useConversationForEntity hook

- **Files**: New `hooks/useConversationForEntity.ts`
- **Changes**:
  ```typescript
  function useConversationForEntity(entityType: string, entityId: string, role: string) {
    return useQuery({
      queryKey: ["conversation", entityType, entityId, role],
      queryFn: () => apiClient.get(`/api/v1/conversations/by-entity`, {
        entity_type: entityType, entity_id: entityId, role
      }),
    });
  }
  ```
- **Why**: Generic hook for any entity type — works for tasks now, stacks/projects later

### Step 6: Wire WorkspaceDetailPage to real ChatRoom

- **Files**: `pages/WorkspaceDetailPage.tsx`
- **Changes**:
  - Use `useConversationForEntity("task", taskId, "execution")` to get conversation
  - If conversation exists, render `<ChatRoom channel={conv.id} />` instead of demo data
  - If no conversation (backlog task), show the current empty state
  - Keep demo data as fallback when no real conversation exists
- **Why**: Connects the workspace to live agent chat with SSE streaming

## Acceptance Criteria

- [ ] Conversation model has `conversation_type` field
- [ ] RelationalPattern links connect conversations to tasks/projects/stacks
- [ ] `GET /conversations/by-entity` returns the right conversation for a task
- [ ] WorkspaceDetailPage shows real ChatRoom when a conversation exists
- [ ] Demo data still renders for tasks without conversations
- [ ] Creating a Job for a Task auto-creates a linked Conversation
- [ ] `branched_from_id` tracks lineage from planning to execution conversations

## Open Questions

1. **Auto-create conversations**: Should hitting the workspace detail page auto-create an execution conversation if one doesn't exist? Or only when a Job starts? Recommend: create on Job start, not on page visit.

2. **Message persistence**: The ChatRoom currently streams via SSE but do messages persist in the DB? The `ConversationRunner` likely handles this — need to verify.

3. **Planning conversations**: Not in scope for this spec. Will be a separate spec when the planning interface is designed. This spec just ensures the association model supports it.
