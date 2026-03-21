---
description: Full SDLC loop from idea to merged code
argument-hint: [idea or issue-id]
---

# /develop

Run the full SDLC loop: Understand → Plan → Spec → Implement → Validate.

Uses **TeamCreate + named teammates** for split-panel visibility and coordinated task management.

## Configuration

Read `.claude/sdlc.yml` for project config. Load primitives:
- `.claude/primitives/language/{language}.md`
- `.claude/primitives/framework/{framework}.md`
- `.claude/primitives/quality/{quality_profile}.md`
- `.claude/primitives/task-management/{task_management}.md`

## Usage

```
/develop Add keyboard shortcuts to the app     # Full loop from idea
/develop SB-NNN                                 # Resume from existing issue
/develop --from=spec SB-NNN                     # Jump to spec phase
/develop --from=implement SB-NNN                # Jump to implementation
```

## Input Detection

1. **Issue ID** (e.g., `SB-NNN`): Read issue from `docs/issues/sb-NNN-*.md`, check for existing spec, resume from appropriate phase.
2. **Free text**: Start from understanding phase, full loop.
3. **`--from=` flag**: Skip to that phase.

## The Loop

```
  ARCHITECT                              BUILDER         VALIDATOR
  ─────────                              ───────         ─────────
  Understand ──[gate]──→ Plan ──[gate]──→ Spec ──[gate]──→ Implement ──→ Validate ──[gate]
                                                            (agentic)
```

Human gates after understand, plan, spec, and validate. Implementation is agentic (no gate).

## Setup

### 1. Create Team

```
TeamCreate(team_name: "develop-{issue-slug}")
```

### 2. Create Tasks

Create one task per phase, with dependencies:

| Task | Subject | Blocked By |
|------|---------|------------|
| #1 | Understand the problem | — |
| #2 | Plan the work breakdown | #1 |
| #3 | Write implementation spec | #2 |
| #4 | Implement the code | #3 |
| #5 | Validate the implementation | #4 |

Skip tasks for phases that are already done (e.g., if `--from=implement`, start at task #4).

---

## Phase 1: Understand

**Spawn teammate:**
```
Agent(
  name: "architect",
  team_name: "develop-{slug}",
  subagent_type: "general-purpose",
  mode: "bypassPermissions",
  prompt: <architect system prompt from .claude/agents/team/architect.md>
         + "Mode: understand"
         + <issue/idea context>
)
```

**Mission:** Demonstrate working knowledge of the problem, codebase, and systems involved.
- Input: User's idea/request ($ARGUMENTS)
- Output: Understanding artifact (context tree + framing statement)
- Constraint: Don't propose solutions — just prove understanding

**On completion:** Architect sends understanding artifact via SendMessage. Shut down architect.

**Human Gate:** "Did I get this right?"

---

## Phase 2: Plan

**Spawn teammate:** Same as Phase 1 but with mode: plan and the approved understanding as input.

**Mission:** Break understood concept into PR-sized issues with dependencies.
- Input: Approved understanding artifact
- Output: Issue tree with dependencies and execution order
- Constraint: Issues sized for single-PR review, parallel work identified

**On completion:** Shut down architect.

**Human Gate:** "Is this the right breakdown?"

**On Approval:** Create issues in `docs/issues/` per task-management primitive.

---

## Phase 3: Spec

**Spawn teammate:** Same architect agent, mode: spec.

**Mission:** Convert issue into implementation spec.
- Input: Issue title + description
- Output: Spec file at `.claude/specs/{issue-slug}.md`
- Constraint: Pseudocode + file list + interfaces, not actual code

**On completion:** Shut down architect.

**Human Gate:** "Is this the right approach?"

---

## Phase 4: Implement

**Spawn teammate:**
```
Agent(
  name: "builder",
  team_name: "develop-{slug}",
  subagent_type: "general-purpose",
  mode: "bypassPermissions",
  prompt: <builder system prompt from .claude/agents/team/builder.md>
         + <spec file path>
)
```

**Mission:** Write code following the approved spec.
- Input: Approved spec file
- Constraint: Follow spec exactly, TDD, run quality gates before done
- Output: Working code on feature branch

**Execution:**
1. Create branch via stack CLI or `git checkout -b dug/{stack}/{index}-{slug}`
2. Implement following spec steps (tests first)
3. Run quality gates (`just quality` or `pts quality`)
4. Commit with conventional style

**On completion:** Builder sends summary via SendMessage. Shut down builder.

**No Human Gate:** Implementation is agentic. Validation provides the checkpoint.

---

## Phase 5: Validate

**Spawn teammate:**
```
Agent(
  name: "validator",
  team_name: "develop-{slug}",
  subagent_type: "general-purpose",
  mode: "bypassPermissions",
  prompt: <validator system prompt from .claude/agents/team/validator.md>
         + <branch name and changed files context>
)
```

**Mission:** Prove the implementation works and meets standards.
- Input: Completed branch from builder
- Output: Validation report (gates, architecture, tests, recommendation)
- If `browser-pilot` skill is available, use it to verify UI changes visually

**On completion:** Validator sends report via SendMessage. Shut down validator.

**Human Gate:** "Ready to merge?"

**On Approval:**
1. `stack submit` to create PR
2. Update issue status

---

## Retry Loop

If validation returns REQUEST_CHANGES:
1. Spawn a new builder with the failure context
2. Builder fixes issues
3. Spawn a new validator
4. Max 3 retries before escalating to human

---

## Shutdown

When all phases complete (or on abort):
1. Shut down any remaining teammates via SendMessage shutdown_request
2. Report final status

---

## Error Handling

- **Phase fails:** Report and ask human — retry, skip, or abort.
- **Validation fails:** Loop back to builder with failure context. Max 3 retries.
- **Blocked issue:** Skip to next unblocked, return when blocker completes.

---

## Team Agents

| Agent | Phases | Capability | Agent Definition |
|-------|--------|------------|-----------------|
| `architect` | Understand, Plan, Spec | Read-only. Explores, plans, specs. | `.claude/agents/team/architect.md` |
| `builder` | Implement | Read-write. Writes code, runs tests. | `.claude/agents/team/builder.md` |
| `validator` | Validate | Runs gates, produces reports. | `.claude/agents/team/validator.md` |

## Relation to /orchestrate

`/develop` handles **one issue**. For multi-epic work, use `/orchestrate` which spawns coordinators that run `/develop` loops per issue.
