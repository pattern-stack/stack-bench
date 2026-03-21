---
id: SB-039
title: Diff Review (diff viewer + backend endpoint)
status: draft
epic: EP-006
depends_on: [SB-038]
branch:
pr:
stack: frontend-mvp
stack_index: 5
created: 2026-03-21
---

# Diff Review (diff viewer + backend endpoint)

## Summary

Build the diff viewer that shows file changes for a selected branch. Includes both the frontend components (diff rendering) and a backend endpoint that produces structured diff data from git. This is the main content panel — the reason someone opens the app.

## Scope

What's in:
- **Backend**: `GET /api/v1/branches/{id}/diff` endpoint
  - Runs `git diff` between branch and its parent (or trunk for first branch)
  - Returns structured JSON: list of files, each with hunks, each with lines
  - Needs workspace `local_path` to know which repo to diff
- **Frontend atoms**:
  - `DiffLine` — single diff line with old/new line numbers, gutter, content. Background color by type (add=green-bg, del=red-bg, context=none, hunk=accent-bg)
  - `DiffBadge` — file change type (A/M/D/R) with semantic color
- **Frontend molecules**:
  - `DiffFileHeader` — DiffBadge + file path (dir dimmed, filename bright) + DiffStat + Chevron. Sticky position. Click to collapse.
  - `DiffHunk` — hunk header line + group of DiffLines
  - `DiffFile` — DiffFileHeader + Collapsible wrapping list of DiffHunks
  - `FileListSummary` — "Showing N changed files with +X additions and -Y deletions"
- **Frontend organism**:
  - `FilesChangedPanel` — FileListSummary + scrollable list of DiffFiles
- Wire into AppShell as the "Files changed" tab content

What's out:
- Side-by-side diff view (unified only for MVP)
- Inline comments on diff lines
- Syntax highlighting
- File tree in sidebar

## Implementation

Key files to create or modify:

```
# Backend
backend/organisms/api/routers/branches.py    # New router with diff endpoint
backend/molecules/apis/diff_api.py           # Git diff execution + parsing

# Frontend
app/frontend/src/components/
  atoms/
    DiffLine/
      DiffLine.tsx
      index.ts
    DiffBadge/
      DiffBadge.tsx
      index.ts
  molecules/
    DiffFileHeader/
      DiffFileHeader.tsx
      index.ts
    DiffHunk/
      DiffHunk.tsx
      index.ts
    DiffFile/
      DiffFile.tsx
      index.ts
    FileListSummary/
      FileListSummary.tsx
      index.ts
  organisms/
    FilesChangedPanel/
      FilesChangedPanel.tsx
      index.ts
```

## Verification

- [ ] `GET /api/v1/branches/{id}/diff` returns structured diff JSON
- [ ] FilesChangedPanel renders all changed files with correct badges (A/M/D/R)
- [ ] Diff lines show correct coloring (green for adds, red for deletes)
- [ ] Hunk headers display with accent background
- [ ] Files are collapsible via chevron click
- [ ] File headers stick to top when scrolling through long diffs
- [ ] Summary line shows correct file count and +/- totals
- [ ] Monospace font throughout diff content

## Notes

Diff JSON structure (proposed):
```json
{
  "files": [
    {
      "path": "src/components/ColumnHeader.tsx",
      "change_type": "modified",
      "additions": 22,
      "deletions": 73,
      "hunks": [
        {
          "header": "@@ -25,7 +25,7 @@ imports",
          "lines": [
            { "type": "context", "old_num": 25, "new_num": 25, "content": "..." },
            { "type": "del", "old_num": 28, "new_num": null, "content": "..." },
            { "type": "add", "old_num": null, "new_num": 28, "content": "..." }
          ]
        }
      ]
    }
  ],
  "total_additions": 211,
  "total_deletions": 358
}
```
