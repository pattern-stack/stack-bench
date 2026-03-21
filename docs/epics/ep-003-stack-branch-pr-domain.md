---
id: EP-003
title: Stack, Branch & PR Domain
status: active
created: 2026-03-19
target:
---

# Stack, Branch & PR Domain

## Objective

Model stacks, branches, and pull requests as first-class domain entities in the backend using pattern-stack. These are the core workflow primitives for the three-tier architecture: local git → stack-bench private workspace → GitHub PRs. Stacks form a DAG (not linear chains), enabling tree-shaped parallel development. Stacks belong to Projects and can span multiple Workspaces (repos).

## Domain Model

```
Stack (EventPattern)
├── project_id: FK → Project
├── name: str
├── base_branch_id: FK → Branch (nullable — null means trunk)
├── trunk: str (e.g. "main" — used when base_branch_id is null)
├── branches: ordered list of Branch
└── states: draft → active → submitted → merged → closed

Branch (EventPattern)
├── stack_id: FK → Stack
├── workspace_id: FK → Workspace (which repo this branch lives in)
├── name: str (git branch name)
├── position: int (order within stack)
├── head_sha: str | None (current commit SHA)
├── pull_request: PullRequest (optional, 1:1)
└── states: created → pushed → reviewing → ready → submitted → merged

PullRequest (EventPattern)
├── branch_id: FK → Branch
├── external_id: int | None (GitHub PR number, null until submitted)
├── external_url: str | None
├── title: str
├── description: str | None
├── review_notes: str | None (private markup — the staging layer)
├── lifecycle exists BEFORE GitHub PR
└── states: draft → open → approved → merged / closed
```

Stack-to-stack dependencies: `Stack.base_branch_id` → any Branch in another stack, forming a DAG. Cross-repo: a stack's branches can reference different workspaces within the same project.

## Protocol/Adapter

```
StackProvider (protocol)
├── StackCLIAdapter     — short-term, wraps existing stack CLI
└── NativeStackAdapter  — long-term, direct git + GitHub API
```

## Issues

| ID | Title | Status | Depends On |
|----|-------|--------|------------|
| SB-014 | Stack feature (model + schemas + service) | draft | SB-027 (Project) |
| SB-015 | Branch feature (model + schemas + service) | draft | SB-014, SB-028 (Workspace) |
| SB-016 | PullRequest feature (model + schemas + service) | draft | SB-015 |
| SB-017 | Stack molecule (StackEntity + StackAPI facade) | draft | SB-014, SB-015, SB-016 |
| SB-018 | StackProvider protocol + StackCLIAdapter | draft | SB-017 |
| SB-019 | REST API routers (stacks, branches, PRs) | draft | SB-017 |
| SB-020 | Alembic migration + seed data | draft | SB-014, SB-015, SB-016 |

## Dependency on EP-005

EP-003 depends on EP-005 (Project & Workspace Domain). Stack needs `project_id`, Branch needs `workspace_id`. Build EP-005 features first, then EP-003.

## Acceptance Criteria

- [ ] Stack, Branch, PullRequest models with state machines in Postgres
- [ ] Stack belongs to Project, Branch belongs to Stack + Workspace
- [ ] Stack DAG: stacks can depend on branches in other stacks
- [ ] Cross-repo: branches in a stack can reference different workspaces
- [ ] PullRequest has private review_notes field (staging layer markup)
- [ ] StackProvider protocol with StackCLIAdapter wrapping existing `stack` binary
- [ ] REST API for CRUD on stacks, branches, PRs
- [ ] Branch lifecycle tracks private workspace state before GitHub PR exists
- [ ] `just test` passes with full coverage of state machines and DAG relationships

## ADRs

- ADR-004: Stack & Branch Domain Model

## Notes

Backend features are the source of truth. The StackCLIAdapter syncs git reality ↔ Postgres. Each feature is ~100-150 lines following pattern-stack conventions (EventPattern, Field, generate_event_service). The `review_notes` field on PullRequest is the seed of the private code review experience — structured feedback before the PR is submitted to GitHub.
