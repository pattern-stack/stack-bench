---
name: project-documentation
description: Create and manage project documentation — ADRs, specs, and architecture docs. Use when the user wants to write an ADR, create a spec, archive a completed spec, or discuss documentation structure.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Project Documentation

## Purpose

Standardize creation and management of project documentation: Architecture Decision Records (ADRs), implementation specs, and the architecture overview. All docs live in `docs/` and follow templates.

## Structure

```
docs/
├── adrs/                    # Architecture Decision Records (append-only)
│   ├── _template.md
│   ├── 001-cli-framework.md
│   └── 002-backend-language.md
├── specs/                   # Implementation specs
│   ├── _template.md
│   ├── archive/             # Completed or abandoned specs
│   └── {date}-{name}.md    # Active specs
└── architecture.md          # Living system overview (optional, created when needed)
```

## Instructions

### Creating an ADR

1. Read `docs/adrs/_template.md` for the format
2. Find the next number by listing existing ADRs: `ls docs/adrs/[0-9]*.md`
3. Create `docs/adrs/{NNN}-{kebab-title}.md` with:
   - Today's date
   - Status: `Draft` (or `Accepted` if decision is final)
   - Filled-in Context, Decision, Options Considered, Consequences
4. Keep it concise — ADRs capture *why*, not *how*

### Creating a Spec

1. Read `docs/specs/_template.md` for the format
2. Create `docs/specs/{YYYY-MM-DD}-{kebab-title}.md` with frontmatter:
   - `status: draft` initially
   - `branch:` if known
   - `depends_on:` list of ADR or spec references
   - `adrs:` related ADR numbers
3. Fill in Goal, Domain Model, Implementation Phases, Open Questions

### Archiving a Spec

1. Add a blockquote at the top: `> **Archived:** {what was built, where, key stats}`
2. Update frontmatter status to `implemented` or `abandoned`
3. Move to `docs/specs/archive/`

### Status Conventions

**ADRs:** `Draft` → `Accepted` → `Superseded by ADR-NNN` (never deleted)

**Specs:** `draft` → `in-progress` → `implemented` | `abandoned` (archived when terminal)

## Key Rules

- Status lives in frontmatter/header, not folder structure. Only `archive/` is a folder-based signal.
- ADRs are numbered and append-only. Superseded ADRs stay in place with updated status.
- Specs are dated. Multiple active specs are fine.
- Don't over-document. If it's in the code or git history, don't repeat it in docs.
