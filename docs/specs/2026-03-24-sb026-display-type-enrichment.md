---
title: "SB-026: Backend display_type enrichment for tool SSE events"
date: 2026-03-24
status: draft
branch:
depends_on: []
adrs: []
issues: [SB-026]
---

# SB-026: Backend display_type enrichment for tool SSE events

## Goal

Add a `display_type` field to `agent.tool.start` and `agent.tool.end` SSE events so CLI and frontend clients know how to render tool results without duplicating tool-name-to-display mapping. This is Phase 1 of the message-parts spec (`docs/specs/2026-03-22-message-parts.md`).

## Architecture Decision

- **Layer:** Molecules (runtime). The ConversationRunner already lives at `molecules/runtime/conversation_runner.py` and is the single point where SSE events are yielded to clients.
- **Pattern:** No new models or patterns. This is a pure enrichment of the SSE serialization path.
- **Subsystems:** None. No DB schema changes, no new migrations, no new services.
- **Approach:** Intercept tool events before SSE formatting. Use `dataclasses.asdict()` to convert the frozen dataclass to a mutable dict, inject `display_type`, then call `formatter.format()` directly instead of `formatter.format_stream_event()`.

## The Mapping

```python
TOOL_DISPLAY_TYPES: dict[str, str] = {
    # File mutations -> diff view
    "edit_file": "diff",
    "write_file": "diff",
    "apply_patch": "diff",
    # Read/search operations -> code view
    "read_file": "code",
    "grep": "code",
    "glob": "code",
    # Shell operations -> bash view
    "bash": "bash",
    "execute_command": "bash",
}
# Default for unknown tools: "generic"
```

This is a module-level constant in `conversation_runner.py`. It can be extended later (pull from `tool_ux` metadata, per-agent overrides) but the SSE contract (`display_type` field present on tool events) is stable.

## File Tree

```
app/backend/src/molecules/runtime/conversation_runner.py   # MODIFY — add mapping + enrichment
app/backend/__tests__/molecules/test_conversation_runner.py # MODIFY — add display_type tests
```

No new files. Two files modified.

## Injection Point

**Current code (line 108-115 of conversation_runner.py):**

```python
async for event in runner.run_stream(agent, message, message_history=message_history):
    # Yield SSE-formatted event
    yield formatter.format_stream_event(event)

    # ... isinstance checks for persistence ...
```

**After change:**

```python
async for event in runner.run_stream(agent, message, message_history=message_history):
    # Enrich tool events with display_type before SSE formatting
    if isinstance(event, (ToolCallStartEvent, ToolCallEndEvent)):
        data = asdict(event)
        data = json.loads(json.dumps(data, default=SSEFormatter._serialize))
        data["display_type"] = TOOL_DISPLAY_TYPES.get(event.tool_name, "generic")
        yield formatter.format(event.event_type, data)
    else:
        yield formatter.format_stream_event(event)

    # ... isinstance checks for persistence (unchanged) ...
```

Key details:
- Import `asdict` from `dataclasses` and `json` (both stdlib).
- Import `SSEFormatter._serialize` is already available since `SSEFormatter` is already imported.
- The serialization step (`json.loads(json.dumps(...))`) mirrors what `format_stream_event` does internally, ensuring UUIDs, datetimes, and enums are handled identically.
- Non-tool events continue through the existing `format_stream_event` path -- zero behavioral change.

## Implementation Steps

1. **Add the `TOOL_DISPLAY_TYPES` constant** at module level, after the imports, before the class definition.
2. **Add imports:** `from dataclasses import asdict` and `import json` at the top of the file.
3. **Modify the SSE yield line** (line 115) to branch on tool event types and inject `display_type`.
4. **Add tests** for display_type enrichment (see Testing Strategy below).
5. **Run existing tests** to confirm no regressions.

## Testing Strategy

### New tests to add (in `test_conversation_runner.py`):

1. **`test_tool_start_event_includes_display_type`** — Send a message through a runner that emits a `ToolCallStartEvent` for `edit_file`. Parse the SSE output and assert `display_type` is `"diff"`.

2. **`test_tool_end_event_includes_display_type`** — Same but for `ToolCallEndEvent`. Assert `display_type` is present.

3. **`test_display_type_mapping_known_tools`** — Parametrized test covering all 8 known tool names and their expected display types.

4. **`test_display_type_defaults_to_generic`** — Emit a tool event with an unknown tool name (e.g., `"custom_tool"`). Assert `display_type` is `"generic"`.

5. **`test_non_tool_events_unchanged`** — Assert that `MessageChunkEvent` and `MessageCompleteEvent` SSE output does NOT contain a `display_type` field.

### Test approach

The tests should use a lightweight mock runner that yields specific event types. Rather than using MockRunner (which requires a tool_executor for tool events), create an inline async generator wrapped in a simple object satisfying `RunnerProtocol.run_stream()`. This is the pattern already used in the existing tests -- they mock `runner.run_stream` via MockRunner's `add_response`.

However, MockRunner's `run_stream` only emits tool events when `tool_calls` is set AND a `tool_executor` is provided. Since ConversationRunner does not pass a tool_executor, the simplest approach is a custom mock:

```python
class _ToolEventRunner:
    """Minimal runner that yields specific tool events for testing."""
    async def run_stream(self, agent, message, **kwargs):
        yield ToolCallStartEvent(tool_call_id="tc_1", tool_name="edit_file", arguments={"path": "test.py"})
        yield ToolCallEndEvent(tool_call_id="tc_1", tool_name="edit_file", result="ok", duration_ms=50)
        yield MessageCompleteEvent(content="Done", input_tokens=5, output_tokens=3)
```

### Markers

All new tests use `@pytest.mark.unit` -- no DB or integration fixtures needed.

### Existing tests

All 8 existing tests in `test_conversation_runner.py` should pass without modification since:
- They use MockRunner which only emits `MessageStartEvent`, `MessageChunkEvent`, and `MessageCompleteEvent` (no tool events).
- The new code only changes behavior for `ToolCallStartEvent` and `ToolCallEndEvent` instances.

## SSE Output Contract

After this change, tool SSE events will include `display_type` as a top-level field:

```
event: agent.tool.start
data: {"tool_call_id": "tc_1", "tool_name": "edit_file", "arguments": {"path": "test.py"}, "display_type": "diff", ...}

event: agent.tool.end
data: {"tool_call_id": "tc_1", "tool_name": "edit_file", "result": "...", "display_type": "diff", ...}
```

Non-tool events are unaffected.

## Open Questions

None. This is a straightforward enrichment with a stable contract. Future enhancements (tool_ux metadata, per-agent overrides) are additive and do not change the SSE field name.
