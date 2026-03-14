# Session Logging Primitive

Structured logging for SDLC workflows. Provides audit trail, resume capability, and human-readable artifacts.

## Philosophy

Sessions are **execution journals** — they capture:
1. What was requested
2. What was decided (human gates)
3. What was produced (artifacts)
4. What happened (logs)

Logs are **git-committed** for traceability and team visibility.

## Directory Structure

```
agent-logs/
└── {session-id}/
    ├── session.yaml           <- Session metadata + state
    ├── request.md             <- Original user request
    │
    ├── phases/                <- Execution trail (ordered)
    │   ├── 1-understand/
    │   │   ├── artifact.md    <- Understanding output
    │   │   └── decision.md    <- Human gate decision
    │   ├── 2-plan/
    │   │   ├── artifact.md    <- Issue tree
    │   │   └── decision.md    <- Human approval + adjustments
    │   └── 3-execute/
    │       ├── {issue-id}/    <- Per-issue execution
    │       │   ├── spec.md
    │       │   ├── implement.log
    │       │   ├── validate.md
    │       │   └── decision.md
    │       └── {issue-id-2}/
    │           └── ...
    │
    ├── gates/                 <- Quality gate outputs
    │   ├── typecheck.log
    │   ├── lint.log
    │   ├── test.log
    │   └── summary.json       <- Structured gate results
    │
    ├── artifacts/             <- Reusable outputs (symlinks or copies)
    │   ├── specs/             <- Links to .claude/specs/
    │   └── branches.md        <- Branch -> issue mapping
    │
    └── summary.md             <- Human-readable session summary
```

## Session ID Format

```
{workflow}-{date}-{hash}
```

Examples:
- `develop-20260314-a3f2`
- `review-20260314-b7c1`
- `hotfix-20260314-d9e4`

## Session YAML Schema

```yaml
# session.yaml
id: develop-20260314-a3f2
workflow: develop
created: 2026-03-14T10:00:00Z
updated: 2026-03-14T14:30:00Z
status: in_progress | completed | abandoned | blocked

# Original request
request:
  raw: "Add keyboard shortcuts to the app"
  parsed:
    type: idea | issue_id | resume
    value: "Add keyboard shortcuts to the app"

# Git context at session start
context:
  branch: feat/keyboard-shortcuts
  base: main
  commit: abc1234

# Current position (for resume)
cursor:
  phase: execute
  issue: SB-042
  step: validate

# Phase statuses
phases:
  understand:
    status: approved
    started: 2026-03-14T10:00:00Z
    completed: 2026-03-14T10:15:00Z

  plan:
    status: approved
    started: 2026-03-14T10:15:00Z
    completed: 2026-03-14T10:30:00Z
    issues:
      - id: SB-042
        title: Create shortcuts registry
        status: done
      - id: SB-043
        title: Add shortcuts UI
        status: implementing

  execute:
    SB-042:
      spec: approved
      implement: done
      validate: passed
      branch: dug/sb-shortcuts/1-registry
      pr: "#123"
    SB-043:
      spec: approved
      implement: in_progress
      validate: pending
      branch: dug/sb-shortcuts/2-ui

# Decisions log (human gates)
decisions:
  - phase: understand
    timestamp: 2026-03-14T10:15:00Z
    gate: "Did I get this right?"
    response: approved
    notes: "Also consider accessibility"

# Errors encountered
errors: []

# Final outputs
outputs:
  issues_created: [SB-042, SB-043]
  prs_created: ["#123"]
  specs_written:
    - .claude/specs/sb-042-shortcuts-registry.md
```

## Session Lifecycle

### 1. Initialize

```bash
WORKFLOW="develop"
HASH=$(openssl rand -hex 2)
SESSION_ID="${WORKFLOW}-$(date +%Y%m%d)-${HASH}"
SESSION_DIR="agent-logs/$SESSION_ID"

mkdir -p "$SESSION_DIR"/{phases/1-understand,phases/2-plan,phases/3-execute,gates,artifacts}
```

### 2. Record Decision

After each human gate:
```bash
cat > "$SESSION_DIR/phases/1-understand/decision.md" <<EOF
# Decision: Understand Gate

**Timestamp**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Gate**: "Did I get this right?"
**Response**: approved

## User Feedback
$USER_RESPONSE

## Adjustments Made
- None
EOF
```

### 3. Finalize Session

```bash
# Update session.yaml status
# Generate summary.md
# Commit to git

git add agent-logs/$SESSION_ID/
git commit -m "docs(session): $SESSION_ID - $WORKFLOW completed

Issues: $ISSUES_CREATED
PRs: $PRS_CREATED

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Resume Protocol

1. Find session: `ls -t agent-logs/ | head -1` or `--resume {session-id}`
2. Load `session.yaml`
3. Read `cursor` to find position
4. Continue from that point
5. Preserve all existing artifacts

## Git Integration

Sessions are committed at:
- Session completion (success or abandon)
- Each phase completion (optional, for long sessions)
- Error states (preserve progress)

## Cleanup Policy

Recommended retention:
- **Completed sessions**: Keep 30 days, then archive or delete
- **Abandoned sessions**: Keep 7 days
- **In-progress sessions**: Keep indefinitely until resolved
