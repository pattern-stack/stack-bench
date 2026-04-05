---
id: EP-016
title: Dashboard Redesign — Navigation, Kanban, Agent Workspaces
status: active
created: 2026-04-05
target: 2026-04-12
---

# Dashboard Redesign

## Objective

Replace the single-stack-only frontend with a three-screen app: kanban task dashboard, agent workspace detail with multi-agent pipeline visualization, and stacks list — all navigated via a persistent global sidebar.

## Specs

- `docs/specs/2026-04-05-dashboard-redesign.md` — Full implementation spec (Phases 1-5)
- `docs/specs/2026-04-05-conversation-associations.md` — ConversationContext wiring
- `docs/adrs/005-conversation-association-model.md` — Architecture decision for polymorphic conversation links

## Design

- `.claude/design/2026-04-04-dashboard-redesign/` — 12 Stitch mockups + DESIGN-DECISIONS.md
- Primary reference: `12-final-workspace-switcher.png`
- Dashboard reference: `03-dashboard-kanban-v3.png`

## PRs

| PR | Branch | Status | What |
|----|--------|--------|------|
| #194 | `dugshub/dashboard-redesign/1-backend-api` | Open | Backend API + 3-screen nav + kanban + workspace chat + stacks list + design tokens |
| #195 | `dugshub/dashboard-redesign/2-conversation-associations` | Open, stacks on #194 | ConversationContext model + by-entity API + ChatRoom wiring + 7 chat component fixes |

## Completed Work

- [x] Task CRUD API + Job→Task linking
- [x] Three-screen routing (/, /workspaces/:taskId, /stacks/:stackId, /stacks)
- [x] GlobalSidebar with nav + active tasks + stacks
- [x] Rich kanban task cards with agent pipeline bars + live status
- [x] Stacks list page with inline branch rows, PR summary, CI status
- [x] Agent workspace with 18-message demo chat (thinking, tool calls, diffs, tables, checklists)
- [x] Chat component tokenization (16 components migrated to --chat-* tokens)
- [x] ADR-005 conversation association architecture
- [x] ConversationContext model (RelationalPattern, aloevera pattern)
- [x] GET /conversations/by-entity endpoint
- [x] useConversationForEntity frontend hook
- [x] WorkspaceDetailPage wired to real ChatRoom with demo fallback
- [x] 7 chat component fixes (thinking blocks, blockquotes, tables, checklists, diffs, tool previews)
- [x] Conversation persistence promoted to agentic-patterns (local, not pushed)

## Open Items

### Visual Polish (from QA)
- [ ] Markdown numbered list spacing still feels off
- [ ] DONE column task cards too cramped
- [ ] Sidebar task names aggressively truncated
- [ ] Done workspace shows wrong branch label
- [ ] Diff line numbers fixed but needs re-verification

### Feature Gaps
- [ ] Wire real agent execution to conversations (currently demo data)
- [ ] Task↔Stack linking (task cards show placeholder diff stats + PR numbers)
- [ ] Drag-and-drop on kanban (currently click-to-move via state transition API)
- [ ] Real-time updates via SSE (event bus infrastructure exists, needs wiring)

### Architecture / Upstream
- [ ] Push conversation persistence to agentic-patterns remote (local changes only)
- [ ] Messages/MessageParts/ToolCalls features not yet promoted to agentic-patterns
- [ ] Frontend component extraction to @pattern-stack/agentic-ui (future)
- [ ] Pattern-stack framework: declarative RelationalPattern on model definitions

### Next Major Feature
- [ ] Planning-first interface — conversational AI for ideation → epics → tasks
