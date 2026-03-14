---
description: Full SDLC loop from idea to merged code
argument-hint: [idea or issue-id]
---

# /develop

Run the full SDLC loop: Understand → Plan → Spec → Implement → Validate.

Three team agents, five phases. Human gates between thinking and building.

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

---

## Phase 1: Understand

**Delegate to:** `team/architect` (understand mode)

**Mission:** Demonstrate working knowledge of the problem, codebase, and systems involved.
- Input: User's idea/request ($ARGUMENTS)
- Output: Understanding artifact (context tree + framing statement)
- Constraint: Don't propose solutions — just prove understanding

**Human Gate:** "Did I get this right?"

---

## Phase 2: Plan

**Delegate to:** `team/architect` (plan mode)

**Mission:** Break understood concept into PR-sized issues with dependencies.
- Input: Approved understanding artifact
- Output: Issue tree with dependencies and execution order
- Constraint: Issues sized for single-PR review, parallel work identified

**Human Gate:** "Is this the right breakdown?"

**On Approval:** Create issues in `docs/issues/` per task-management primitive.

---

## Phase 3: Spec

**Delegate to:** `team/architect` (spec mode)

**Mission:** Convert issue into implementation spec.
- Input: Issue title + description
- Output: Spec file at `.claude/specs/{issue-slug}.md`
- Constraint: Pseudocode + file list + interfaces, not actual code

**Human Gate:** "Is this the right approach?"

---

## Phase 4: Implement

**Delegate to:** `team/builder`

**Mission:** Write code following the approved spec.
- Input: Approved spec file
- Constraint: Follow spec exactly, TDD, run `make ci` before done
- Output: Working code on feature branch

**Execution:**
1. Create branch via stack CLI or `git checkout -b dug/{stack}/{index}-{slug}`
2. Implement following spec steps (tests first)
3. Run quality gates (`make ci`)
4. Commit with conventional style

**No Human Gate:** Implementation is agentic. Validation provides the checkpoint.

---

## Phase 5: Validate

**Delegate to:** `team/validator`

**Mission:** Prove the implementation works and meets standards.
- Input: Completed branch from builder
- Output: Validation report (gates, architecture, tests, recommendation)

**Human Gate:** "Ready to merge?"

**On Approval:**
1. `stack submit` to create PR
2. Update issue status

---

## Error Handling

- **Phase fails:** Report and ask human — retry, skip, or abort.
- **Validation fails:** Loop back to builder with failure context. Max 3 retries.
- **Blocked issue:** Skip to next unblocked, return when blocker completes.

---

## Team Agents

| Agent | Phases | Capability |
|-------|--------|------------|
| `team/architect` | Understand, Plan, Spec | Read-only. Explores, plans, specs. |
| `team/builder` | Implement | Read-write. Writes code, runs tests. |
| `team/validator` | Validate | Read-only. Runs gates, produces reports. |
