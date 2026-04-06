---
title: Agent Execution Wiring
date: 2026-04-05
status: draft
branch: dugshub/dashboard-redesign/2-conversation-associations
depends_on: [2026-04-05-conversation-associations]
adrs: [ADR-005]
---

# Agent Execution Wiring

## Goal

Wire real agent execution to conversations so the workspace UI shows live agent chat instead of demo data. Replace the placeholder `POST /conversations/{id}/send` with a streaming endpoint backed by `ConversationRunner`, bridge Job execution to conversations, and provide a stub agent that proves the pipeline end-to-end without requiring an API key.

## Context

### What exists

- **ConversationRunner** (`molecules/runtime/conversation_runner.py`) — fully implemented molecule that loads conversation history, assembles an agent via `AgentAssembler`, streams execution through `RunnerProtocol`, yields SSE-formatted events, and persists messages + tool calls + token counts back to DB.
- **Send endpoint** (`organisms/api/routers/conversations.py:73-85`) — placeholder `POST /conversations/{id}/send` that returns `{"status": "received"}`.
- **SSE infrastructure** (`organisms/api/routers/events.py`) — `/events/stream?channel={channel}` endpoint with Broadcast subsystem. Frontend `useEventSource` hook connects to this.
- **Broadcast bridge** (`molecules/events/handlers/broadcast_bridge.py`) — bridges EventBus domain events to Broadcast channels. Currently routes to `global` and `stack:{id}` channels.
- **ConversationContext** (`features/conversations/models.py`) — RelationalPattern linking conversations to tasks/jobs via `entity_a_type="conversation"`, `entity_b_type="task"|"job"`.
- **TaskAPI.create_job_for_task()** (`molecules/apis/task_api.py:159-204`) — already auto-creates a Conversation + ConversationContext links when creating a job for a task.
- **Frontend ChatRoom** (`components/organisms/ChatRoom/ChatRoom.tsx`) — connects to SSE via `useEventSource({channel})`, renders messages via `useChatMessages`, accepts `onSendMessage` callback. WorkspaceDetailPage renders ChatRoom when `useConversationForEntity` returns a conversation.
- **Frontend SSE_EVENT_MAP** (`types/chat.ts`) — maps backend SSE event names (`agent.message.chunk`, `agent.tool.start`, `agent.tool.end`, `agent.message.complete`, `agent.error`) to StreamChunkTypes.
- **ConversationRunnerDep** (`organisms/api/dependencies.py:126-130`) — FastAPI dependency already defined but unused.
- **AgentAssembler** (`molecules/agents/assembler.py`) — builds `Agent` objects from DB-stored AgentDefinition + RoleTemplate records.
- **Job model** (`features/jobs/models.py`) — states: `queued → running → gated → complete/failed/cancelled`.
- **Job handlers** (`molecules/events/job_handlers.py`) — registered at startup, currently stubs.

### What's missing

1. The send endpoint is a placeholder — it doesn't call ConversationRunner or stream anything.
2. No broadcast bridge for conversation-scoped events — the bridge only routes to `global` and `stack:{id}` channels.
3. No Job→Conversation execution trigger — when a Job starts running, nothing kicks off agent execution.
4. No stub agent — the system requires a seeded AgentDefinition + RoleTemplate and a working `RunnerProtocol` to function. Without an API key, agent execution fails silently.

## Domain Model

| Entity | Pattern | Role in this spec |
|--------|---------|-------------------|
| Conversation | EventPattern | Target of send endpoint, container for messages |
| Message / MessagePart | BasePattern | Persisted by ConversationRunner during streaming |
| ConversationContext | RelationalPattern | Links conversation ↔ job/task (already exists) |
| Job | EventPattern | Triggers agent execution on state transition |
| AgentDefinition | BasePattern | Defines agent config (needs stub seed) |
| RoleTemplate | BasePattern | Defines agent persona (needs stub seed) |

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Wire send endpoint to ConversationRunner with SSE streaming | -- |
| 2 | Job→Conversation bridge: trigger agent on Job "running" | Phase 1 |
| 3 | Stub agent: echo runner + seed data | Phase 1 |

## Phase Details

### Phase 1: Wire send endpoint

**Goal**: Replace the placeholder `POST /conversations/{id}/send` with a real streaming response that calls `ConversationRunner.send()` and broadcasts events to the conversation's SSE channel.

**Files to modify**:
- `organisms/api/routers/conversations.py` — replace placeholder with StreamingResponse
- `molecules/events/handlers/broadcast_bridge.py` — add conversation-scoped channel routing
- `molecules/events/topics.py` — add conversation event topics
- `molecules/events/setup.py` — register conversation topics with broadcast bridge

#### 1a. Replace send endpoint with streaming response

The endpoint should:
1. Accept `POST /conversations/{id}/send` with `{"message": "..."}`.
2. Call `ConversationRunner.send(conversation_id, message)`.
3. Return a `StreamingResponse` with `media_type="text/event-stream"` that yields SSE events from the runner.
4. Simultaneously broadcast each SSE event to the conversation's broadcast channel (`conversation:{id}`) so that other SSE clients (the workspace UI) receive live updates.

```python
@router.post("/{conversation_id}/send")
async def send_message(
    conversation_id: UUID,
    data: SendMessageRequest,
    runner: ConversationRunnerDep,
) -> StreamingResponse:
    async def generate() -> AsyncGenerator[str, None]:
        broadcast = get_broadcast()
        async for sse_chunk in runner.send(conversation_id, data.message):
            yield sse_chunk
            # Parse and broadcast to conversation channel for other listeners
            await _broadcast_sse_chunk(broadcast, conversation_id, sse_chunk)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })
```

The `_broadcast_sse_chunk` helper parses the SSE-formatted string to extract `event:` and `data:` fields, then calls `broadcast.broadcast(f"conversation:{conversation_id}", event_type, data)`.

#### 1b. Add conversation channel to broadcast bridge

Update `broadcast_bridge.py` to also route events to `conversation:{id}` when the payload contains `conversation_id`:

```python
if isinstance(payload, dict) and "conversation_id" in payload:
    conv_id = payload["conversation_id"]
    await broadcast.broadcast(f"conversation:{conv_id}", event.event_type, data)
```

This enables the existing `/events/stream?channel=conversation:{id}` path to deliver conversation-scoped events. The frontend `useEventSource` already subscribes to arbitrary channels.

#### 1c. Frontend: wire onSendMessage to POST endpoint

The WorkspaceDetailPage already renders `<ChatRoom channel={conversation.id} ... />`. Update the `channel` prop to use `conversation:{conversation.id}` and wire `onSendMessage` to POST to `/api/v1/conversations/{id}/send`.

This is a minimal frontend change:
- Pass `channel={`conversation:${conversation.id}`}` to ChatRoom
- Pass `onSendMessage` that calls `apiClient.post(`/api/v1/conversations/${conversation.id}/send`, { message: text })`

### Phase 2: Job→Conversation bridge

**Goal**: When a Job transitions to `running`, find its linked conversation and trigger agent execution with the job's input text as the initial message.

**Files to modify**:
- `molecules/events/topics.py` — add `JOB_STARTED` topic (or reuse Job state transition event)
- `molecules/events/job_handlers.py` — add handler for job execution trigger
- New: `molecules/runtime/job_execution_bridge.py` — orchestrates Job→Conversation→Runner

#### 2a. Enable Job state transition events and listen for "running"

The Job model does NOT currently have `emit_state_transitions = True`. Add it to the Job model's Pattern class so state transitions are automatically emitted. Then subscribe to the "running" transition.

**Files to modify (additional):**
- `features/jobs/models.py` — add `emit_state_transitions = True` to Pattern class

If for any reason automatic emission is insufficient, add an explicit `JOB_STARTED = "job.started"` topic and publish it from the job handler when the job starts running.

#### 2b. Job execution bridge

Create `molecules/runtime/job_execution_bridge.py`:

```python
async def execute_job_conversation(
    db: AsyncSession,
    job_id: UUID,
) -> None:
    """Find the conversation linked to a job and trigger agent execution."""
    # 1. Find conversation linked to this job
    conv_svc = ConversationService()
    context = await conv_svc.get_conversation_for_entity(
        db, entity_type="job", entity_id=job_id, role="execution",
    )
    if context is None:
        logger.warning("No conversation linked to job %s", job_id)
        return

    # 2. Load the job for its input_text
    job = await job_service.get(db, job_id)
    prompt = job.input_text or f"Execute job {job.reference_number}"

    # 3. Run through ConversationRunner (fire-and-forget stream consumption)
    runner = ConversationRunner(db)
    async for _chunk in runner.send(context.conversation_id, prompt):
        pass  # Events are broadcast via the runner; we just drain the stream
```

#### 2c. Wire into job handler

In `job_handlers.py`, when a job starts (or in a new event handler), call `execute_job_conversation`. This should run as a background task (via `asyncio.create_task` or the Jobs subsystem) to avoid blocking the state transition.

### Phase 3: Stub agent

**Goal**: Create a stub agent that proves the full pipeline without requiring an ANTHROPIC_API_KEY. Must be easily swappable for a real agent later.

**Files to create/modify**:
- New: `molecules/runtime/stub_runner.py` — echo-based RunnerProtocol implementation
- `molecules/runtime/conversation_runner.py` — use stub runner when no API key configured
- Seed data: add stub agent definition + role template to `seeds/`

#### 3a. StubRunner (echo mode)

Implement `RunnerProtocol` with an echo runner that simulates agent behavior:

```python
class StubRunner:
    """Echo runner for development/testing when no API key is available."""

    def run_stream(
        self, agent: Agent, message: str, *,
        message_history: list | None = None,
        tool_executor=None, hooks=None, event_bus=None,
        max_iterations: int = 10, trace_id=None, parent_span_id=None,
    ) -> AsyncIterator[StreamEvent]:
        async def _generate():
            yield ReasoningEvent(content="Processing request...")
            yield MessageChunkEvent(content=f"Echo: {message}")
            yield MessageCompleteEvent(
                content=f"Echo: {message}",
                input_tokens=0,
                output_tokens=0,
            )
        return _generate()
```

Note: `run_stream` is NOT async — it returns an async iterator synchronously, matching `RunnerProtocol`'s actual signature. All keyword parameters from the protocol are accepted and ignored by the stub.

This produces valid SSE events that the frontend can render, proving the full pipeline.

#### 3b. Runner selection in ConversationRunner

Update `_get_default_runner()` to check for `ANTHROPIC_API_KEY`:

```python
def _get_default_runner(self) -> RunnerProtocol:
    from config.settings import get_settings
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        from molecules.runtime.stub_runner import StubRunner
        return StubRunner()
    from agentic_patterns.core.systems.runners.agent import AgentRunner
    return AgentRunner()
```

This keeps runner selection in one place. When a real API key is configured, the production `AgentRunner` is used automatically. The `agent_runner` parameter on `send()` still allows injection for testing.

#### 3c. Seed stub agent

Add seed data for an "orchestrator" agent — this name is hardcoded in `TaskAPI.create_job_for_task()` at `task_api.py:179`. No "orchestrator" currently exists in `seeds/agents.yaml` (only: understander, planner, specifier, implementer, reviewer).

- **RoleTemplate**: name="orchestrator", persona for task orchestration
- **AgentDefinition**: name="orchestrator", role_template="orchestrator", mission="Orchestrate task execution"

Name the seed "orchestrator" (not "stub") so it matches the hardcoded value. The stub runner makes the agent name irrelevant to behavior — when a real agent replaces the stub, the same seed works.

## Key Design Decisions

1. **Dual delivery**: The send endpoint returns SSE directly to the caller AND broadcasts to the conversation channel. This means both the direct API caller and any workspace UI watching the conversation channel receive events. The direct response is needed for request/response semantics; the broadcast is needed for the workspace view which connects via a separate SSE stream.

2. **No new domain events for message streaming**: ConversationRunner already yields SSE events from agentic-patterns. Rather than converting these to DomainEvents and back, we broadcast the SSE chunks directly to the conversation channel. This avoids double-serialization and keeps the streaming path simple.

3. **Stub runner, not stub agent**: The pluggability point is `RunnerProtocol`, not the agent definition. The `Agent` object is always assembled from the DB — the stub runner simply ignores it and echoes. This means the same seed data works for both stub and real execution.

4. **Background execution for jobs**: Job→Conversation execution runs as a background task, not inline with the job state transition. This prevents the event handler from blocking and allows the conversation stream to run independently.

## Acceptance Criteria

- [ ] `POST /conversations/{id}/send` returns `StreamingResponse` with SSE events
- [ ] SSE events are broadcast to `conversation:{id}` channel
- [ ] Frontend ChatRoom receives streamed messages when `onSendMessage` is called
- [ ] StubRunner produces valid SSE events without an API key
- [ ] When `ANTHROPIC_API_KEY` is set, `AgentRunner` is used instead of `StubRunner`
- [ ] Job "running" transition triggers agent execution on linked conversation
- [ ] Existing tests pass; new tests cover send endpoint and stub runner
- [ ] No frontend changes beyond wiring `onSendMessage` and `channel` prop

## Open Questions

1. **Broadcast parsing**: `ConversationRunner.send()` currently yields bare `str` (SSE-formatted). To broadcast, we need to extract event type and data. **Decision**: Modify `send()` to yield `(event_type: str, data_dict: dict, sse_string: str)` tuples. This is a breaking change to the signature, but send() has no callers today (the endpoint is a placeholder). The endpoint uses `sse_string` for the StreamingResponse; the broadcast helper uses `event_type` and `data_dict`. This avoids fragile SSE string parsing.

2. **Agent name for job conversations**: `TaskAPI.create_job_for_task()` hardcodes `agent_name="orchestrator"`. Should this be configurable per-task, or is "orchestrator" the right default for now? Recommend: keep "orchestrator" as default, ensure it has a seed.

3. **Error handling on job execution**: If the conversation runner fails mid-stream during job execution, should the job transition to "failed"? Recommend: yes, wrap the bridge in try/except and transition the job to "failed" with the error message.
