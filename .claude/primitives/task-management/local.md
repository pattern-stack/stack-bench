# Local Task Management Primitive

Issues stored as markdown files in the repo. No external tracker required.

## Concepts

| Local Term | Generic Term | Description |
|------------|--------------|-------------|
| Issue file | Work Item | `docs/issues/sb-NNN-slug.md` |
| Epic file | Epic | `docs/epics/ep-NNN-slug.md` |
| Frontmatter | Metadata | YAML frontmatter in each file |
| Status field | State | Edited directly in frontmatter |

## Issue Structure

Issues live at `docs/issues/sb-NNN-slug.md`:

```yaml
---
id: SB-001
title: Project bootstrap
status: draft          # draft | ready | in-progress | review | done | blocked
epic: EP-001
depends_on: []
branch: dug/sb-backend/1-bootstrap
pr:
stack: sb-bootstrap
stack_index: 1
parallel_with: []
created: 2026-03-14
---

# Project Bootstrap

## Summary
What this issue delivers.

## Scope
What's in and what's out.

## Verification
- [ ] Acceptance criteria as checklist
```

## Epic Structure

Epics live at `docs/epics/ep-NNN-slug.md`:

```yaml
---
id: EP-001
title: Backend Bootstrap
status: active         # planning | active | completed
issues: [SB-001, SB-002, SB-003]
---

# Backend Bootstrap

High-level description of the epic.
```

## Workflow States

```
draft → ready → in-progress → review → done
                    ↓
                 blocked
```

## Status Updates

Edit frontmatter directly:
```bash
# No CLI needed — just edit the file
# Change status: draft → in-progress
```

## Label Conventions

Use frontmatter fields instead of labels:
- `epic:` — groups related issues
- `stack:` — which PR stack this belongs to
- `depends_on:` — blocking dependencies
- `parallel_with:` — can be worked simultaneously

## CLI Reference

No external CLI needed. Issues are just files:

```bash
# List issues
ls docs/issues/

# Find in-progress issues
grep -l "status: in-progress" docs/issues/*.md

# Create new issue
cp docs/issues/_template.md docs/issues/sb-NNN-slug.md
# Edit frontmatter and content
```

## Naming Convention

- Issue IDs: `SB-NNN` (stack-bench project prefix)
- File names: `sb-NNN-slug.md` (lowercase, kebab-case)
- Branch names: `dug/stack-name/index-description`
