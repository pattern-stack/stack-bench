---
id: EP-006
title: Frontend MVP — Stack Review UI
status: planning
created: 2026-03-21
target: 2026-03-22
---

# Frontend MVP — Stack Review UI

## Objective

Ship a React frontend that lets a developer select a branch from their stack, view the diff, and see PR metadata — the core "review your own stacked PRs" loop. Built on pattern-stack conventions (Vite, Tailwind 4, pts codegen), with atoms borrowed from dealbrain's component library and completely restyled with a new dark design system.

## Issues

| ID | Title | Status | Branch |
|----|-------|--------|--------|
| SB-035 | Frontend scaffold + dark design system | draft | -- |
| SB-036 | Shared atoms (Badge, Icon, Button, Collapsible, Tab) | draft | -- |
| SB-037 | Stack Navigation (sidebar + branch list) | draft | -- |
| SB-038 | App Shell + Chrome (layout, tabs, PR header) | draft | -- |
| SB-039 | Diff Review (diff viewer + backend endpoint) | draft | -- |

## Acceptance Criteria

- [ ] `pts dev` starts frontend on configured port, proxies `/api` to backend
- [ ] Stack sidebar loads branches from `GET /api/v1/stacks/{id}/detail`
- [ ] Clicking a branch shows its PR title, branch info, and diff
- [ ] Diff view shows file list with add/modify/delete badges and collapsible unified diffs
- [ ] Dark theme with custom design tokens (not dealbrain styling)
- [ ] Atoms are generic, reusable, and cleanly separated from domain components

## Development Orchestration

### Execution Model

Use **teammate mode** with specialized agents. Each issue is built by a builder agent with a reviewer validating before marking complete.

### Team Roles

| Role | Responsibility |
|------|---------------|
| **Architect** (you) | Read the issue, plan file layout, identify atoms to borrow from dealbrain. Produce a build brief for the builder. |
| **Builder** (teammate) | Implement the issue. Write components, styles, hooks. Must follow `atomic-frontend-developer` skill rules. |
| **Validator** (teammate) | After build: start the app, open browser, verify components render correctly. Check logs for errors. Run `pts quality` if applicable. |

### Dev Loop Per Issue

1. **Read the issue** — load `docs/issues/sb-NNN-*.md`
2. **Architect** — identify dealbrain source atoms, plan adaptations, draft component APIs
3. **Builder** — implement in `app/frontend/src/components/`. Follow atomic design rules.
4. **Launch & verify**:
   - Start backend: `pts services up && cd backend && just migrate`
   - Start frontend: `cd app/frontend && npm run dev`
   - Open `http://localhost:3500` in browser
   - Check browser console for errors
   - Check terminal for Vite/build errors
5. **Validate** — components render, dark theme applied, no console errors
6. **Commit & stack** — `stack push` to add branch to stack

### Quality Checks

Before marking any issue done:
- [ ] No TypeScript errors (`npm run type-check` or `tsc --noEmit`)
- [ ] No Vite build errors (dev server starts clean)
- [ ] Components render on dark background with correct tokens
- [ ] No hardcoded colors — all `var(--token-name)` references
- [ ] Atoms have zero domain imports (no Stack, Branch, PR types)
- [ ] Molecules use callback props, no data fetching

### Skills Available

| Skill | When to use |
|-------|-------------|
| `atomic-frontend-developer` | Component architecture decisions, layer placement |
| `run-and-monitor` | Starting the dev environment, checking logs, debugging |
| `pattern-stack` | Backend patterns, service architecture, API conventions |

### Source Material

| Resource | Location | Purpose |
|----------|----------|---------|
| V3 mockup | `app/frontend/mockups/stack-review-v3.html` | Visual reference for layout and dark theme |
| Dealbrain atoms | `/Users/dug/Projects/dealbrain2/apps/frontend/src/components/atoms/` | Component structure to borrow (Badge, Icon, Button, Collapsible) |
| Dealbrain tokens | `/Users/dug/Projects/dealbrain2/apps/frontend/src/styles/tokens.css` | Token structure reference (NOT the actual values — we restyle everything) |
| Design token values | V3 mockup CSS `:root` block | Our dark palette source of truth |

## Notes

- Conversation domain excluded — being built in CLI first (EP-002), will port structure later
- Atoms borrowed from dealbrain for structure only — completely restyled with dark design system
- Frontend patterns (`@pattern-stack/frontend-patterns`) used as component library foundation
- `pts sync generate` provides API client, Zod schemas, TanStack Query hooks from backend models
- Stack CLI manages branches: `stack create frontend-mvp`, then `stack push` per issue
