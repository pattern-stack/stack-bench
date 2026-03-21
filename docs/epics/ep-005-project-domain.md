---
id: EP-005
title: Project & Workspace Domain
status: active
created: 2026-03-19
target:
---

# Project & Workspace Domain

## Objective

Model projects and workspaces as the top-level ownership layer in stack-bench. A project is the anchor entity that stacks, conversations, jobs, and environments hang off of. A project can span multiple git repositories (workspaces). Stacks belong to projects, not workspaces, enabling cross-repo stacking.

## Domain Model

```
Project (EventPattern)
├── name: str
├── description: str | None
├── metadata_: dict (settings, provider config)
├── states: setup → active → archived
├── owns: Workspace[], Stack[], Conversation[] (optional)
│
├── Workspace (BasePattern)
│   ├── project_id: FK → Project
│   ├── name: str (display name)
│   ├── repo_url: str (GitHub/GitLab URL)
│   ├── provider: str (github | gitlab | bitbucket)
│   ├── default_branch: str (e.g. "main")
│   ├── local_path: str | None (path on disk)
│   ├── metadata_: dict (clone config, remote state)
│   └── is_active: bool
│
└── Worktree (BasePattern)
    ├── workspace_id: FK → Workspace
    ├── branch_id: FK → Branch (nullable, from EP-003)
    ├── path: str (absolute path on disk)
    ├── is_default: bool (is this the main worktree?)
    ├── metadata_: dict
    └── is_active: bool
```

Project owns workspaces — not the other way around — because:
- A project can have multiple repos (monorepo + infra, microservices, etc.)
- Stacks can cross repos (coordinated changes across workspace boundaries)
- The project is the user's mental model of "the thing I'm building"

Worktree models a local git worktree as a first-class entity, bridging the "local git" tier to the private workspace tier. A Workspace (repo) can have multiple Worktrees (local checkouts). Each Worktree is optionally linked to a Branch from EP-003.

## Issues

| ID | Title | Status | Depends On |
|----|-------|--------|------------|
| SB-027 | Project feature (model + schemas + service) | draft | -- |
| SB-028 | Workspace feature (model + schemas + service) | draft | SB-027 |
| SB-029 | Project + Workspace REST API routers | draft | SB-027, SB-028 |
| SB-030 | Wire Stack.project_id FK | draft | SB-027, SB-014 |
| SB-031 | Wire Branch.workspace_id FK | draft | SB-028, SB-015 |
| SB-032 | Wire Conversation.project_id FK (optional) | draft | SB-027 |
| SB-033 | Alembic migration for project + workspace | draft | SB-027, SB-028 |
| SB-034 | Worktree feature (model + schemas + service) | draft | SB-028 |

Note: SB-034 was added during spec review as extended scope. It models the local git worktree as a first-class entity, bridging the "local git" tier to the private workspace tier. Worktree belongs to a Workspace and optionally references a Branch (from EP-003). The `branch_id` FK on Worktree is nullable and deferred until EP-003 tables exist.

## Acceptance Criteria

- [ ] Project model with EventPattern + state machine in Postgres
- [ ] Workspace model linked to Project via FK
- [ ] A project can have multiple workspaces (repos)
- [ ] Worktree model linked to Workspace via FK, optionally linked to Branch
- [ ] Stack belongs to Project, Branch belongs to Stack + Workspace
- [ ] REST API for project and workspace CRUD
- [ ] Conversation optionally linked to Project
- [ ] `just test` passes

## ADRs

- ADR-004: Stack & Branch Domain Model

## Notes

Keep Project thin -- it's an anchor and ownership boundary, not a god object. Workspace is the repo-level entity. Worktree is the local checkout entity. Don't model the git object graph -- that's git's job. The provider field on Workspace enables future multi-provider support (GitHub, GitLab, etc.).
