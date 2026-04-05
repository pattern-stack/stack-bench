---
title: "EP-015 Orchestration: Web Chat Parity Execution Plan"
status: draft
date: 2026-04-04
epic: EP-015
type: orchestration
spec: .claude/specs/2026-04-04-web-chat-parity.md
---

# EP-015 Orchestration: Web Chat Parity Execution Plan

## Purpose

This document is the execution playbook for building EP-015 (Web Chat Parity). It defines how to use `/orchestrate` and `/develop` to systematically build all 25 issues across 6 layers, maximizing parallelism while respecting dependencies.

## How to Run

```
/orchestrate EP-015
```

The lead coordinator reads this spec and the companion implementation spec (`.claude/specs/2026-04-04-web-chat-parity.md`), then executes the waves below.

---

## Execution Strategy

EP-015 is a single epic with 25 issues. The lead coordinator spawns **one coordinator** (`coordinator-015`) which owns all 25 issues and runs `/develop` loops for each.

Within each wave, independent issues run in **parallel** `/develop` loops. Waves are sequential — a wave cannot start until its predecessor completes.

```
/orchestrate EP-015
 └── coordinator-015 (owns all 25 issues)
      ├── Wave 1: Foundation (4 parallel /develop loops)
      ├── Wave 2: Atoms (8 parallel /develop loops)
      ├── Wave 3: Molecules (7 parallel /develop loops)
      ├── Wave 4: Message Rendering (2 sequential /develop loops)
      ├── Wave 5: Input & Commands (2 sequential /develop loops)
      └── Wave 6: Organism & Migration (2 sequential /develop loops)
```

---

## Wave Definitions

### Wave 1: Foundation

**Goal:** Establish types, tokens, and streaming infrastructure. Everything else depends on this.

| Issue | Title | Parallel Group | Dependencies |
|-------|-------|---------------|--------------|
| SB-120 | Chat Message Types | A | — |
| SB-121 | Chat Design Tokens | A | — |
| SB-122 | useEventSource Hook | B (after SB-120) | SB-120 |
| SB-123 | useChatMessages Reducer | C (after SB-122) | SB-120, SB-122 |

**Execution order:**
1. `/develop SB-120` and `/develop SB-121` — run in parallel (Group A)
2. `/develop SB-122` — after SB-120 completes (Group B)
3. `/develop SB-123` — after SB-122 completes (Group C)

**Human gate:** After Wave 1, verify types and tokens are solid — everything builds on them.

**Develop guidance per issue:**
- **SB-120**: Architect reads `app/cli/internal/chat/model.go` and `app/cli/internal/api/client.go` for exact type definitions. Builder writes `app/frontend/src/types/chat.ts`. Validator checks all CLI types are covered.
- **SB-121**: Architect reads `app/cli/internal/ui/theme/tokens.go` and `app/frontend/src/index.css` for existing tokens. Builder adds `--chat-*` CSS custom properties to `index.css`. Validator checks all 4 categories, 6 statuses, 4 hierarchy levels present.
- **SB-122**: Architect reads `app/cli/internal/api/sse.go` and `app/backend/src/organisms/api/routers/events.py`. Builder writes `app/frontend/src/hooks/useEventSource.ts`. Validator checks all 7 event types + aliases handled.
- **SB-123**: Architect reads CLI chat model update logic. Builder writes `app/frontend/src/hooks/useChatMessages.ts` using `useReducer`. Validator checks chunk → message accumulation for all part types.

---

### Wave 2: Atoms

**Goal:** Build all atomic components — both code-focused and conversational. All depend on SB-121 (tokens) only.

| Issue | Title | Parallel Group |
|-------|-------|---------------|
| SB-124 | ChatCodeBlock | All parallel |
| SB-125 | ChatSpinner | All parallel |
| SB-126 | ChatInlineCode | All parallel |
| SB-127 | ChatSeparator | All parallel |
| SB-140 | ChatRoleIndicator | All parallel |
| SB-141 | ChatTimestamp | All parallel |
| SB-142 | ChatPresenceIndicator | All parallel |
| SB-144 | ChatNotice | All parallel |

**Execution order:** All 8 issues run in parallel after Wave 1 completes.

**Practical note:** Running 8 parallel `/develop` loops may be resource-intensive. The coordinator may split into two sub-waves if needed:
- **Wave 2a** (code atoms): SB-124, SB-125, SB-126, SB-127
- **Wave 2b** (conversational atoms): SB-140, SB-141, SB-142, SB-144

**Develop guidance per issue:**
- **All atoms**: Builder places components in `app/frontend/src/components/atoms/{ComponentName}/`. Follow existing atom patterns (see `Badge/`, `Icon/` for reference). Each atom gets a `.tsx` file, a `.module.css` file, and an `index.ts` barrel export. Use `atomic-frontend-developer` skill rules.
- **SB-124 (ChatCodeBlock)**: Reuse Shiki infrastructure from `app/frontend/src/lib/shiki.ts`. Reference CLI's `atoms/codeblock.go` for features (language label, line numbers, gutter).
- **SB-125 (ChatSpinner)**: CSS `@keyframes` only, no JS intervals. Two sizes: `sm` and `md`.
- **SB-140 (ChatRoleIndicator)**: Match CLI convention — `you:`, `sb:`, `sys:`. Accept custom agent name override.
- **SB-142 (ChatPresenceIndicator)**: Renders ONLY the animation. Role indicator is the parent's responsibility.
- **SB-144 (ChatNotice)**: Centered, non-attributed. Three variants: info/warning/error.

---

### Wave 3: Molecules

**Goal:** Compose atoms into higher-order chat components.

| Issue | Title | Dependencies | Parallel Group |
|-------|-------|-------------|---------------|
| SB-143 | ChatMessageGroup | SB-140, SB-141, SB-127 | All parallel |
| SB-128 | ChatMarkdown | SB-121, SB-124, SB-126 | All parallel |
| SB-129 | ChatStatusBlock | SB-125 | All parallel |
| SB-130 | ChatToolCallBlock | SB-124, SB-125 | All parallel |
| SB-131 | ChatDiffBlock | SB-121 | All parallel |
| SB-132 | ChatThinkingBlock | SB-121 | All parallel |
| SB-133 | ChatErrorBlock | SB-121 | All parallel |

**Execution order:** All 7 run in parallel after Wave 2 completes.

**Practical note:** Same as Wave 2 — coordinator may split if needed:
- **Wave 3a** (code molecules): SB-128, SB-129, SB-130, SB-131, SB-132, SB-133
- **Wave 3b** (conversational molecule): SB-143

**Develop guidance per issue:**
- **All molecules**: Builder places in `app/frontend/src/components/molecules/{ComponentName}/`. Same file pattern as atoms.
- **SB-128 (ChatMarkdown)**: This is the most complex molecule. Architect should evaluate markdown parsing libraries (e.g., `react-markdown`, `marked`, or custom parser). Must handle streaming (partial/incomplete markdown). Reference CLI's `ui/markdown.go` for feature set.
- **SB-130 (ChatToolCallBlock)**: Three states: running (spinner + "running"), success (check + "done"), error (X + "failed"). Expandable/collapsible for input/output sections. Reference CLI's `molecules/toolcallblock.go`.
- **SB-131 (ChatDiffBlock)**: Include `parseUnifiedDiff()` utility matching CLI's implementation. Green for additions, red for deletions.
- **SB-143 (ChatMessageGroup)**: Layout wrapper with `children` slot — does NOT render ChatMessageRows internally. Parent (ChatRoom) composes groups and rows.

---

### Wave 4: Message Rendering

**Goal:** Wire molecules into the message dispatch and rendering pipeline.

| Issue | Title | Dependencies |
|-------|-------|-------------|
| SB-134 | MessagePart Dispatcher | SB-128–133 |
| SB-135 | ChatMessageRow | SB-134, SB-129, SB-140–142 |

**Execution order:** Sequential — SB-134 first, then SB-135.

**Develop guidance:**
- **SB-134**: Switch on `part.type` → render correct molecule. Handle `ToolCallPart.displayType` routing (diff → ChatDiffBlock, code/bash → ChatCodeBlock, generic → default). Unknown types get fallback rendering.
- **SB-135**: Composes ChatRoleIndicator + ChatTimestamp + part list via dispatcher + ChatPresenceIndicator for pre-stream state. This is where the full message experience comes together.

---

### Wave 5: Input & Commands

**Goal:** Build the chat input and slash command system. Runs in parallel with Wave 4 (no dependency overlap).

| Issue | Title | Dependencies |
|-------|-------|-------------|
| SB-136 | ChatInput | SB-121 |
| SB-137 | SlashCommandAutocomplete | SB-136, SB-121 |

**Execution order:** Sequential — SB-136 first, then SB-137.

**Note:** Wave 5 can run **in parallel with Wave 4** since they share no dependencies beyond completed earlier waves.

**Develop guidance:**
- **SB-136**: Auto-resize textarea. Enter submits, Shift+Enter newline. Detect `/` prefix for autocomplete trigger. Disabled state during streaming.
- **SB-137**: Fuzzy + prefix matching. Reference CLI's `autocomplete/autocomplete.go` for matching algorithm. Keyboard nav: up/down arrows, Tab, Enter to select, Esc to dismiss. Max 6 visible suggestions. Built-in commands: `/help`, `/clear`, `/agents`.

---

### Wave 6: Organism & Migration

**Goal:** Assemble everything into the final ChatRoom organism and migrate AgentPanel.

| Issue | Title | Dependencies |
|-------|-------|-------------|
| SB-138 | ChatRoom Organism | SB-123, SB-135, SB-143, SB-144, SB-136, SB-137 |
| SB-139 | AgentPanel Migration | SB-138 |

**Execution order:** Sequential — SB-138 first, then SB-139.

**Human gate:** After SB-138, review the ChatRoom organism in browser before migrating AgentPanel.

**Develop guidance:**
- **SB-138**: This is the integration point. Composes ChatMessageGroup[] wrapping ChatMessageRow[], wires useChatMessages + useEventSource, manages auto-scroll, renders ChatInput + SlashCommandAutocomplete. Empty state for no messages. ChatNotice for operational events. Builder should place in `app/frontend/src/components/organisms/ChatRoom/`.
- **SB-139**: Surgical migration — AgentPanel keeps its collapsible sidebar shell, but swaps internal mock logic for ChatRoom. Wire to real `/api/v1/conversations/` endpoint. Validator must verify: toggle/collapse still works, real conversation created on first message, SSE streaming active.

**Final validation:** Validator uses `browser-pilot` to:
1. Open the app
2. Open AgentPanel
3. Send a message
4. Verify multi-part message rendering
5. Check console for errors
6. Verify slash command autocomplete works

---

## Parallel Execution Summary

```
Time →

Wave 1:  [SB-120 | SB-121] → [SB-122] → [SB-123]
                    ↓
Wave 2:  [SB-124 | SB-125 | SB-126 | SB-127 | SB-140 | SB-141 | SB-142 | SB-144]
                    ↓
Wave 3:  [SB-128 | SB-129 | SB-130 | SB-131 | SB-132 | SB-133 | SB-143]
                    ↓                                              ↓
Wave 4:  [SB-134] → [SB-135]              Wave 5: [SB-136] → [SB-137]
                    ↓                                  ↓
Wave 6:            [SB-138] → [SB-139]
```

**Waves 4 and 5 run in parallel** — they have no shared dependencies.

**Estimated total `/develop` loops:** 25
**Maximum parallel loops in a single wave:** 8 (Wave 2)
**Critical path:** SB-121 → SB-124 → SB-128 → SB-134 → SB-135 → SB-138 → SB-139 (7 sequential issues)

---

## Human Gates

| When | Gate | What to Review |
|------|------|---------------|
| After Wave 1 | Foundation Review | Types match CLI. Tokens cover all dimensions. SSE hook connects. |
| After Wave 2 | Atoms Review | All 8 atoms render correctly. Design tokens applied. |
| After Wave 3 | Molecules Review | Complex components work: markdown streaming, tool call lifecycle, diff rendering, message grouping. |
| After SB-138 | Organism Review | Full ChatRoom experience in browser. Multi-part messages, streaming, slash commands. |
| After SB-139 | Final Review | AgentPanel migration complete. Real API wired. No regressions. |

---

## Error Handling

| Scenario | Response |
|----------|----------|
| Atom fails validation | Fix and retry (max 3). Atoms are self-contained — failures don't cascade. |
| ChatMarkdown (SB-128) is complex | Allow extra retries. Consider splitting markdown parsing from React rendering if needed. |
| SSE hook (SB-122) can't connect | Check backend is running (`pts dev`). Verify `/api/v1/events/stream` endpoint. |
| Wave blocked by unresolved dependency | Coordinator skips blocked issues, completes unblocked ones, returns when blocker resolves. |
| Quality gates fail | Builder fixes. Validator re-runs. Max 3 retries per issue before escalating. |

---

## Branch Strategy

All work happens on a single feature branch per issue, following the naming convention:

```
dug/ep-015-web-chat/{layer}-{slug}
```

Examples:
- `dug/ep-015-web-chat/0-chat-types`
- `dug/ep-015-web-chat/1a-chat-code-block`
- `dug/ep-015-web-chat/1b-chat-role-indicator`
- `dug/ep-015-web-chat/2-chat-markdown`
- `dug/ep-015-web-chat/5-chat-room`

Each `/develop` loop creates its branch, implements, validates, and commits. The coordinator tracks branch names for the final integration.

---

## Quality Gates Per Issue

Every `/develop` loop's validator runs:

1. **TypeScript compilation**: `npx tsc --noEmit` (no type errors)
2. **Lint**: `npx eslint` on changed files
3. **Tests**: Component tests pass (if the issue includes tests)
4. **Visual verification**: For atoms/molecules, validator can use `browser-pilot` to render in Storybook or dev mode (if available)
5. **Integration check**: For Wave 6, full end-to-end flow in browser

---

## Post-Orchestration

When all 25 issues complete:

1. Coordinator reports final status per issue
2. Lead coordinator summarizes what was built
3. Human reviews full ChatRoom experience in browser
4. If approved, issues are merged and epic status updated to `completed`
