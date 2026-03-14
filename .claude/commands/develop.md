---
description: Full SDLC loop from idea to merged code
argument-hint: [idea or issue-id]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task, WebFetch, WebSearch
primitives:
  required:
    - language          # Determines implementation patterns
    - task_management   # Where issues live (system-specific behavior)
    - session-logging   # Execution journal and audit trail
  optional:
    - quality_profile   # strict or fast validation
    - commit_style      # conventional or freeform
    - framework         # framework-specific patterns
---

# /develop

Run the full SDLC loop: Understand -> Plan -> Spec -> Implement -> Validate.

Each loop has a human gate. Sessions are logged for audit trail and resume capability.

## Configuration

Read `.claude/sdlc.yml` for project config. Load primitives:
- `.claude/primitives/language/{language}.md` for language conventions
- `.claude/primitives/framework/{framework}.md` for framework patterns (if configured)
- `.claude/primitives/quality/{quality_profile}.md` for validation gates
- `.claude/primitives/task-management/{task_management}.md` for issue tracking

## Usage

```
/develop Add keyboard shortcuts to the app     # Full loop from idea
/develop SB-NNN                                 # Resume from existing issue
/develop --from=spec SB-NNN                     # Jump to spec phase
/develop --resume                               # Resume most recent session
/develop --resume {session-id}                   # Resume specific session
/develop --no-logging                            # Disable session logging
```

## Input Detection

Determine what was provided:

1. **Issue ID** (e.g., `SB-NNN`):
   - Read issue from `docs/issues/sb-NNN-*.md` (or configured task tracker)
   - Check for existing spec in `.claude/specs/`
   - Resume from appropriate phase

2. **Free text**:
   - Start from understanding phase
   - Full loop

3. **`--from=` flag**:
   - `--from=understand` - Start fresh
   - `--from=plan` - Skip to planning (assumes understanding exists)
   - `--from=spec` - Skip to specification
   - `--from=implement` - Skip to implementation
   - `--from=validate` - Skip to validation

## The Loops

```
+---------------------------------------------------------------------------+
|                                                                           |
|  +-----------+    +--------+    +------+    +-----------+    +--------+   |
|  | UNDERSTAND|--->|  PLAN  |--->| SPEC |--->| IMPLEMENT |--->|VALIDATE|   |
|  +-----+-----+    +---+----+    +--+---+    +-----+-----+    +---+----+   |
|        |              |            |              |              |        |
|        v              v            v              |              v        |
|   [Human Gate]   [Human Gate] [Human Gate]       |        [Human Gate]   |
|   "Got it?"      "Right        "Right            |        "Merge?"       |
|                   breakdown?"   approach?"       |                       |
|                                                  |                       |
|                              +-------------------+                       |
|                              | (agentic - no gate)                       |
|                              v                                           |
|                    Parallel execution for subtasks                       |
|                                                                           |
+---------------------------------------------------------------------------+
```

---

## Phase 1: Understand

**Delegate to:** `understander` agent

**Mission:**
- **Objective:** Demonstrate working knowledge of the problem, application, and systems
- **Input:** User's idea/request ($ARGUMENTS)
- **Context:** Codebase structure, existing patterns, relevant files
- **Constraints:** Don't propose solutions yet - just prove understanding
- **Output:** Understanding artifact (context tree + framing statement)

**Human Gate:** Present understanding, ask "Did I get this right?"

**On Approval:** Proceed to Plan phase

---

## Phase 2: Plan

**Delegate to:** `planner` agent

**Mission:**
- **Objective:** Break understood concept into PR-sized issues with dependencies
- **Input:** Approved understanding artifact
- **Context:** Recent PRs (for sizing), task tracker conventions, existing issues
- **Constraints:**
  - Issues sized for single-PR review
  - Subtasks indicate parallel work
  - Use task tracker conventions as configured in `task_management` primitive
- **Output:** Issue tree with dependencies

**Human Gate:** Present issue tree, ask "Is this the right breakdown?"

**On Approval:**
1. Create issues (use `task_management` primitive for system-specific behavior)
2. Proceed to Spec phase for first unblocked issue

---

## Phase 3: Spec

**Delegate to:** `specifier` agent (one per issue)

**Mission:**
- **Objective:** Convert issue into implementation spec (pseudocode, files, API)
- **Input:** Issue title + description
- **Context:** Understanding artifact, related specs, codebase patterns
- **Constraints:**
  - Pseudocode level - not full implementation
  - Must list all files touched (new + modified)
  - Must define interfaces/types
- **Output:** Spec file at `.claude/specs/{issue-slug}.md`

**Human Gate:** Present spec, ask "Is this the right approach?"

**On Approval:** Proceed to Implement phase

---

## Phase 4: Implement

**Delegate to:** `implementer` agent (one per issue)

**Mission:**
- **Objective:** Write code following the approved spec
- **Input:** Approved spec file
- **Context:**
  - Language primitive for patterns
  - Framework primitive for architecture rules
  - Existing codebase patterns
- **Constraints:**
  - Follow spec exactly - no scope creep
  - One commit per logical change
  - Run quality gates before marking complete
- **Output:** Working code on feature branch

**Execution:**
1. Create branch: `dug/{stack-name}/{index}-{description}` (stack CLI convention)
2. Implement following spec steps
3. Run quality gates (per `quality_profile` primitive)
4. Commit with configured commit style

**No Human Gate:** Implementation is agentic. Validation phase provides the checkpoint.

---

## Phase 5: Validate

**Delegate to:** `validator` agent

**Mission:**
- **Objective:** Prove the implementation works
- **Input:** Completed branch from implementer
- **Context:** Quality profile, test patterns
- **Constraints:** Must pass all gates before approval
- **Output:** Validation report

**Human Gate:** Present validation report, ask "Ready to merge?"

**On Approval:**
1. Create PR (use stack CLI: `stack submit`)
2. Update issue status

---

## Session Logging

**See:** `.claude/primitives/session-logging.md` for full specification.

Sessions are logged to `agent-logs/{session-id}/`.

### Session Initialization

At command start (skip if `--no-logging`):

```bash
SESSION_ID="develop-$(date +%Y%m%d)-$(openssl rand -hex 2)"
SESSION_DIR="agent-logs/$SESSION_ID"
mkdir -p "$SESSION_DIR"/{phases/1-understand,phases/2-plan,phases/3-execute,gates}
```

### Resume Protocol

1. `--resume` finds most recent in-progress session
2. Load `session.yaml`, read `cursor` for position
3. Continue from that phase/issue
4. Preserve all existing artifacts

---

## Error Handling

**Phase fails:**
1. Report what went wrong
2. Ask human how to proceed:
   - Retry with adjustments
   - Skip to next phase
   - Abort

**Validation fails:**
1. Report failing gates
2. Loop back to implementer with failure context
3. Max 3 retries before human intervention

**Blocked issue:**
1. Skip to next unblocked issue
2. Return when blocker completes

---

## Dependencies

This command uses:

| Component | Type | Purpose |
|-----------|------|---------|
| `understander` | agent | Demonstrates problem understanding |
| `planner` | agent | Breaks down into issues |
| `specifier` | agent | Creates implementation specs |
| `implementer` | agent | Writes code |
| `validator` | agent | Runs validation gates |
| `task_management` | primitive | System-specific issue creation/updates |
| `session-logging` | primitive | Execution journal and audit trail |
