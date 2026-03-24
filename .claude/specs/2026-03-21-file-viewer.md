---
title: File Viewer — Source Browser for Branch Files
date: 2026-03-21
status: draft
branch: dugshub/file-viewer/1-file-viewer-scaffold
depends_on: [frontend-mvp#6-syntax-highlighting]
adrs: []
---

# File Viewer — Source Browser for Branch Files

## Goal

Add a read-only file browser to Stack Bench so users can view the full source tree and file contents for any branch in a stack. This provides context alongside the existing diff view — users can inspect any file, not just changed files. The viewer reuses the existing Shiki syntax highlighting pipeline and plugs into the AppShell tab system as a new "Source" tab.

## Domain Model

No new database models. The file viewer reads from the git worktree on disk via the backend. Two new read-only endpoints return the file tree and file content for a given branch.

```
FileTreeNode (API schema only, not persisted)
  - name: str              # filename or directory name
  - path: str              # full relative path from repo root
  - type: "file" | "dir"
  - children: FileTreeNode[] | null  # populated for dirs, null for files
  - size: int | null       # byte size for files, null for dirs

FileContent (API schema only, not persisted)
  - path: str
  - content: str           # raw file contents (utf-8, truncated for binary)
  - size: int
  - is_binary: bool
  - language: str | null    # detected language for syntax highlighting
```

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Backend endpoints (tree + file content) | -- |
| 2 | Frontend file tree + file content viewer + tab integration | Phase 1 |

## Phase Details

### Phase 1: Backend Endpoints

**Layer placement** (following atoms → features → molecules → organisms):

- **Feature**: `features/git_files/` — new feature with no DB model, only schemas and a service that wraps git/filesystem operations
- **Molecule**: Not needed — single-feature, no cross-feature coordination
- **Organism**: `organisms/api/routers/branches.py` — new router (branch-scoped endpoints)

#### Endpoint 1: `GET /api/v1/branches/{branch_id}/tree`

Returns the recursive file tree for a branch's worktree.

**How it works**: Look up the Branch by ID → get its workspace → use `workspace.local_path` to find the repo root → walk the directory tree, excluding `.git/` and common ignore patterns.

Request:
```
GET /api/v1/branches/{branch_id}/tree
Query params:
  - path: str = ""          # subtree root (empty = repo root)
  - depth: int = -1         # max recursion depth (-1 = unlimited)
```

Response (200):
```json
{
  "root": {
    "name": ".",
    "path": "",
    "type": "dir",
    "children": [
      {
        "name": "src",
        "path": "src",
        "type": "dir",
        "children": [
          {
            "name": "App.tsx",
            "path": "src/App.tsx",
            "type": "file",
            "children": null,
            "size": 2048
          }
        ],
        "size": null
      }
    ],
    "size": null
  }
}
```

**Schemas** (`features/git_files/schemas/output.py`):
```python
class FileTreeNodeResponse(BaseModel):
    name: str
    path: str
    type: Literal["file", "dir"]
    children: list["FileTreeNodeResponse"] | None = None
    size: int | None = None

class FileTreeResponse(BaseModel):
    root: FileTreeNodeResponse
```

**Service** (`features/git_files/service.py`):
```python
class GitFileService:
    """Read-only access to files in a workspace's local repo.

    No DB model — this wraps filesystem operations. Sits at the features
    layer because it's a single-concern service (file reading), not a
    cross-feature orchestrator.
    """

    async def get_tree(self, repo_path: str, *, sub_path: str = "", depth: int = -1) -> FileTreeNodeResponse: ...
    async def get_file_content(self, repo_path: str, file_path: str) -> FileContentResponse: ...
```

#### Endpoint 2: `GET /api/v1/branches/{branch_id}/file`

Returns the content of a single file.

Request:
```
GET /api/v1/branches/{branch_id}/file
Query params:
  - path: str (required)    # relative file path
```

Response (200):
```json
{
  "path": "src/App.tsx",
  "content": "import { useState } from 'react';\n...",
  "size": 2048,
  "is_binary": false,
  "language": "tsx"
}
```

**Schemas** (`features/git_files/schemas/output.py`):
```python
class FileContentResponse(BaseModel):
    path: str
    content: str
    size: int
    is_binary: bool
    language: str | None = None
```

**Language detection**: Port the same extension map from the frontend's `lang-from-path.ts` to Python in the service.

**Security**: The service must validate that `file_path` doesn't escape the repo root (no `../` traversal). Return 400 for paths outside the worktree.

**Binary files**: Detect binary content (null bytes in first 8KB). Return `is_binary: true` with an empty `content` string and no `language`.

**Router** (`organisms/api/routers/branches.py`):
```python
router = APIRouter(prefix="/branches", tags=["branches"])

@router.get("/{branch_id}/tree", response_model=FileTreeResponse)
async def get_branch_tree(branch_id: UUID, path: str = "", depth: int = -1, db: DatabaseSession) -> FileTreeResponse: ...

@router.get("/{branch_id}/file", response_model=FileContentResponse)
async def get_branch_file(branch_id: UUID, path: str = Query(...), db: DatabaseSession) -> FileContentResponse: ...
```

**Wire-up**: Register `branches_router` in `app.py` alongside existing routers.

**Files to create/modify**:
```
app/backend/src/features/git_files/__init__.py        (new)
app/backend/src/features/git_files/service.py         (new)
app/backend/src/features/git_files/schemas/__init__.py (new)
app/backend/src/features/git_files/schemas/output.py  (new)
app/backend/src/organisms/api/routers/branches.py     (new)
app/backend/src/organisms/api/app.py                  (modify — add branches_router)
```

---

### Phase 2: Frontend File Tree + Content Viewer + Tab Integration

**Atomic design placement**:

#### Types

`types/file-tree.ts` — new type file:
```typescript
export interface FileTreeNode {
  name: string;
  path: string;
  type: "file" | "dir";
  children: FileTreeNode[] | null;
  size: number | null;
}

export interface FileContent {
  path: string;
  content: string;
  size: number;
  is_binary: boolean;
  language: string | null;
}
```

#### Atoms

**`FileIcon`** (`components/atoms/FileIcon/`) — renders a file or folder icon based on `type: "file" | "dir"` and optionally the file extension. Uses the existing `Icon` atom pattern. Minimal: just distinguish file vs folder, with expand/collapse chevron for folders.

**`LineNumber`** (`components/atoms/LineNumber/`) — styled line number gutter cell for the file content viewer. Reuses the same visual style as `DiffLine` gutters for consistency.

#### Molecules

**`FileTreeItem`** (`components/molecules/FileTreeItem/`) — a single row in the file tree. Renders `FileIcon` + file name, with indent level based on depth. Clickable for files (selects), clickable for folders (toggles expand/collapse). Highlights the active file.

**`FileContent`** (`components/molecules/FileContent/`) — displays syntax-highlighted file content with line numbers. Uses the existing `highlightCode()` from `lib/shiki.ts` and `langFromPath()` from `lib/lang-from-path.ts`. Shows a "Binary file" placeholder for binary files. Structure:

```
┌─ file path breadcrumb ─────────────────┐
│ 1 │ import { useState } from 'react';  │
│ 2 │                                    │
│ 3 │ export function App() {            │
│ ...                                    │
└────────────────────────────────────────┘
```

#### Organisms

**`FileTree`** (`components/organisms/FileTree/`) — recursive tree built from `FileTreeItem` molecules. Manages expand/collapse state internally. Props: `tree: FileTreeNode`, `selectedPath: string | null`, `onSelectFile: (path: string) => void`. Directories sorted before files, both alphabetical.

**`FileViewerPanel`** (`components/organisms/FileViewerPanel/`) — the top-level panel that combines `FileTree` + `FileContent` in a split layout. This is the `children` content rendered inside AppShell when the "Source" tab is active.

Layout:
```
┌──────────────┬──────────────────────────────┐
│  FileTree    │  FileContent                 │
│  (sidebar)   │  (main area)                 │
│  ~250px      │  flex-1                      │
│              │                              │
│  ▸ src/      │  src/App.tsx                 │
│    App.tsx ← │  1 │ import ...              │
│    index.ts  │  2 │ ...                     │
│  ▸ docs/     │                              │
└──────────────┴──────────────────────────────┘
```

#### Hooks

**`useFileTree`** (`hooks/useFileTree.ts`) — fetches the file tree for a branch. Follows the same pattern as `useBranchDiff`:
```typescript
export function useFileTree(branchId: string | undefined): {
  data: FileTreeNode | null;
  loading: boolean;
  error: string | null;
}
```
MVP: returns mock data. Wire to `GET /api/v1/branches/{branch_id}/tree` when backend is ready.

**`useFileContent`** (`hooks/useFileContent.ts`) — fetches file content for a selected path:
```typescript
export function useFileContent(branchId: string | undefined, path: string | null): {
  data: FileContent | null;
  loading: boolean;
  error: string | null;
}
```
MVP: returns mock data. Wire to `GET /api/v1/branches/{branch_id}/file?path=...` when backend is ready.

**`useHighlightedFile`** (`hooks/useHighlightedFile.ts`) — takes `FileContent`, runs it through `highlightCode()` via the Shiki singleton, returns highlighted HTML lines. Follows the same async pattern as `useHighlightedDiff`:
```typescript
export function useHighlightedFile(file: FileContent | null): {
  highlightedLines: string[];
  loading: boolean;
}
```

#### State Management

- **Selected file path**: Lifted to `App.tsx` as `useState<string | null>(null)`. Passed down to `FileViewerPanel`. Resets when switching branches.
- **Tree expand/collapse**: Internal to `FileTree` organism via `useState<Set<string>>`. Paths of expanded directories. Defaults: expand first level only.

#### Tab Integration

In `App.tsx`, add a "Source" tab to the `tabs` array:
```typescript
const tabs: TabItem[] = [
  { id: "files", label: "Files changed", count: fileCount || undefined },
  { id: "source", label: "Source" },
];
```

Conditionally render content based on `activeTab`:
```typescript
{activeTab === "files" && diffData && <FilesChangedPanel diffData={diffData} />}
{activeTab === "source" && <FileViewerPanel branchId={activeBranchId} />}
```

No changes needed to `AppShell`, `TabBar`, or `Tab` — they already support dynamic tabs via the `tabs` prop.

#### Shiki Integration

Reuse the existing singleton from `lib/shiki.ts`:
- `getHighlighter()` — same shared instance, no new themes/setup
- `highlightCode(code, lang)` — called from `useHighlightedFile` with the full file content
- `langFromPath(path)` — determines language for the highlight call

For large files (>5000 lines), skip highlighting and render plain text to avoid perf issues.

**Files to create/modify**:
```
app/frontend/src/types/file-tree.ts                              (new)
app/frontend/src/components/atoms/FileIcon/FileIcon.tsx          (new)
app/frontend/src/components/atoms/FileIcon/index.ts              (new)
app/frontend/src/components/atoms/LineNumber/LineNumber.tsx       (new)
app/frontend/src/components/atoms/LineNumber/index.ts            (new)
app/frontend/src/components/atoms/index.ts                       (modify — add exports)
app/frontend/src/components/molecules/FileTreeItem/FileTreeItem.tsx  (new)
app/frontend/src/components/molecules/FileTreeItem/index.ts      (new)
app/frontend/src/components/molecules/FileContent/FileContent.tsx    (new)
app/frontend/src/components/molecules/FileContent/index.ts       (new)
app/frontend/src/components/molecules/index.ts                   (modify — add exports)
app/frontend/src/components/organisms/FileTree/FileTree.tsx      (new)
app/frontend/src/components/organisms/FileTree/index.ts          (new)
app/frontend/src/components/organisms/FileViewerPanel/FileViewerPanel.tsx  (new)
app/frontend/src/components/organisms/FileViewerPanel/index.ts   (new)
app/frontend/src/hooks/useFileTree.ts                            (new)
app/frontend/src/hooks/useFileContent.ts                         (new)
app/frontend/src/hooks/useHighlightedFile.ts                     (new)
app/frontend/src/lib/mock-file-data.ts                           (new — mock tree + file content)
app/frontend/src/App.tsx                                         (modify — add Source tab + FileViewerPanel)
```

## Issue Breakdown

### SB-040: Backend File Endpoints (tree + content)

**Stack**: `file-viewer`, **Index**: 1, **Branch**: `dugshub/file-viewer/1-file-viewer-scaffold`

- Create `features/git_files/` with service and schemas
- Create `organisms/api/routers/branches.py` with two endpoints
- Register router in `app.py`
- Tests for path traversal protection, binary detection, tree walking

### SB-041: Frontend File Viewer (tree + content + tab integration)

**Stack**: `file-viewer`, **Index**: 2, **Branch**: `dugshub/file-viewer/2-file-viewer-frontend`

- Types, atoms (`FileIcon`, `LineNumber`), molecules (`FileTreeItem`, `FileContent`)
- Organisms (`FileTree`, `FileViewerPanel`)
- Hooks (`useFileTree`, `useFileContent`, `useHighlightedFile`) with mock data
- Tab integration in `App.tsx`
- Mock data file for development

## Stack Strategy

```
file-viewer stack (base: frontend-mvp#6-syntax-highlighting)
  1. dugshub/file-viewer/1-file-viewer-scaffold  → SB-040 (backend endpoints)
  2. dugshub/file-viewer/2-file-viewer-frontend   → SB-041 (frontend + tab)
```

Two issues keeps backend and frontend cleanly separated. The frontend issue includes tab integration since it's a one-line change in `App.tsx` and doesn't warrant its own branch.

## Open Questions

1. **Large file handling**: Should we set a max file size for content retrieval (e.g., 1MB)? Current plan: return content up to 1MB, return `is_binary: true` with empty content for larger files.
2. **Git ref vs worktree**: Current design reads from `workspace.local_path` on disk. If we want to read from arbitrary git refs (not just the checked-out branch), we'd need `git show ref:path`. Deferring to a future iteration.
3. **Gitignore respect**: Should the tree endpoint respect `.gitignore`? Initial plan: exclude `.git/` and `node_modules/` hardcoded, but show everything else. Could use `git ls-tree` instead of os.walk to automatically respect gitignore.
