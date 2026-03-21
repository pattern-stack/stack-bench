# ADR-004: Stack & Branch Domain Model

**Date:** 2026-03-19
**Status:** Draft
**Deciders:** Dug

## Context

Stack Bench needs to model git workflow concepts — projects, workspaces, stacks, branches, and pull requests — as first-class domain entities in the backend. The existing stack CLI (dugshub/stack) handles stacking operations today but stores state in JSON files (~/.claude/stacks/). We need backend-owned domain models that support:

1. A three-tier workflow: local git → stack-bench private workspace → GitHub PRs
2. Multi-repo projects where stacks can span repositories
3. Stack-to-stack dependencies forming a DAG (not just linear chains)
4. A private review/markup layer before code reaches the team
5. Eventually replacing the stack CLI entirely via a protocol/adapter pattern

## Decision

### Three-Tier Architecture

Stack Bench introduces a **private workspace tier** between local git and GitHub:

```
Local (git)
    ↓ push
Stack-Bench Private (Postgres + web UI)
    ↓ submit
GitHub (team PRs)
```

- **push** syncs branches from local git to the stack-bench workspace (Postgres). This is a developer-private staging area — not visible to the team.
- **submit** promotes from the private workspace to real GitHub PRs.

The private workspace enables: stack visualization (Graphite-like), agent orchestration against your code (Conductor-like), structured code markup/feedback, and narrative refinement — all before anyone else sees the work.

### Domain Model

```
Project (EventPattern) — top-level owner
├── Workspace[] — git repositories linked to this project
│   └── repo_url, provider, default_branch, local_path
├── Stack[] — belongs to project, NOT workspace
│   ├── Branch[] — each branch tied to a workspace
│   │   └── PullRequest (1:1, optional)
│   └── base: Branch in another stack, or trunk
└── Conversation[] — optionally linked to project

Stack (EventPattern)
├── project_id: FK → Project
├── base_branch_id: FK → Branch (nullable — null means trunk)
├── trunk: str (used when base_branch_id is null)
└── state machine: draft → active → submitted → merged → closed

Branch (EventPattern)
├── stack_id: FK → Stack
├── workspace_id: FK → Workspace (which repo)
├── position: int (order within stack)
├── head_sha: str | None
└── state machine: created → pushed → reviewing → ready → submitted → merged

PullRequest (EventPattern)
├── branch_id: FK → Branch
├── external_id: int | None (GitHub PR number, null until submitted)
├── review_notes: str | None (private markup)
└── state machine: draft → open → approved → merged / closed
```

### Why Project Owns Workspaces (Not the Reverse)

- A project can span multiple repos (monorepo + infra + docs, microservices, etc.)
- Stacks can cross repos — coordinated changes across workspace boundaries
- The project is the user's mental model of "the thing I'm building"
- Stacks belong to the project because they represent a unit of work, not a unit of code

### Stack-to-Stack Dependencies (DAG)

Stacks can depend on other stacks at arbitrary points, not just tips:

```
Stack A: [branch 1] → [branch 2] → [branch 3] → [branch 4] → [branch 5]
                                         ↑
Stack C: [branch 1] → [branch 2] → [branch 3]
         (base = Stack A, branch 3)

Stack B: [branch 1] → [branch 2] → [branch 3] → [branch 4] → [branch 5]
         (base = Stack A, branch 5 — i.e. tip)
```

Sibling stacks can fork from the same point, forming a tree.

### Cross-Repo Stacking

A single stack can have branches in different workspaces:

```
Stack "full-feature":
  Branch 1: backend-repo → api-endpoint        (workspace: backend)
  Branch 2: frontend-repo → ui-component       (workspace: frontend)
  Branch 3: infra-repo → terraform-config      (workspace: infra)
```

Each branch references its workspace via `workspace_id`. The stack owns the ordering and dependencies; the workspace owns the git context.

### CLI Command Taxonomy

Two namespaces with clean separation:

**sb stack ...** — operations on the stack as a whole (workflow verbs):
- `sb stack push` / `sb stack push 1 3 5` — sync to stack-bench private workspace
- `sb stack submit` — promote to GitHub PRs
- `sb stack create` / `sb stack status` / `sb stack sync` / `sb stack restack`

**sb branch ...** — operations on a branch within a stack (membership + reshaping):
- `sb branch add` / `sb branch add --at 3` — add branch to stack at position
- `sb branch remove` — remove branch from stack
- `sb branch fold` — fold branch into parent
- `sb branch split 3` — break a branch into multiple
- `sb branch absorb` — route fixes to correct branches

Top-level aliases for 80% commands: `sb create`, `sb status`, `sb submit`, `sb up/down`, `sb modify`.

### Protocol/Adapter for Git Operations

```python
class StackProvider(Protocol):
    """Contract for git stacking operations."""
    async def create_stack(name, trunk) -> ...: ...
    async def push(stack) -> ...: ...
    async def submit(stack) -> ...: ...
    async def restack(stack) -> ...: ...
    async def sync(stack) -> ...: ...

class StackCLIAdapter(StackProvider):
    """Short-term: wraps existing stack CLI binary."""

class NativeStackAdapter(StackProvider):
    """Long-term: direct git + GitHub API operations."""
```

## Consequences

- **Private workspace is the core product differentiator.** Graphite + Conductor in one — iterate with agents before publishing.
- **Multi-repo projects** reflect real-world development. Most non-trivial projects span repos.
- **Cross-repo stacking** is a capability competitors don't offer. Coordinated changes across repos in one stack.
- **DAG model is more complex than linear stacks** but reflects real development patterns.
- **Protocol/adapter enables incremental migration** from the stack CLI without a flag day.
- **Branch lifecycle exists before GitHub PRs** — the `pushed → reviewing → ready` states happen in the private workspace.
- **PullRequest.review_notes** is the seed of the private code review experience — structured feedback before submission.
