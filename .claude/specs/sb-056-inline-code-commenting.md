---
title: "SB-056: Inline code commenting"
status: in-progress
issue: "#93"
epic: EP-009
---

# SB-056: Inline Code Commenting

## Overview

Allow highlighting diff lines and leaving inline comments, synced to GitHub PR review comments. Comments live in our DB as the source of truth and sync to GitHub.

## Backend Implementation

### Step 1: Create ReviewComment feature

Create `app/backend/src/features/review_comments/` with:

**`__init__.py`**: Empty or minimal exports

**`models.py`**:
```python
from uuid import UUID
from pattern_stack.atoms.patterns import BasePattern, Field

class ReviewComment(BasePattern):
    __tablename__ = "review_comments"

    class Pattern:
        entity = "review_comment"
        reference_prefix = "RC"
        track_changes = True

    pull_request_id = Field(UUID, foreign_key="pull_requests.id", required=True, index=True)
    branch_id = Field(UUID, foreign_key="branches.id", required=True, index=True)
    path = Field(str, required=True, max_length=500)
    line_key = Field(str, required=True, max_length=200)
    line_number = Field(int, nullable=True)
    side = Field(str, nullable=True, max_length=10)
    body = Field(str, required=True)
    author = Field(str, required=True, max_length=200)
    external_id = Field(int, nullable=True)
    resolved = Field(bool, default=False)
```

**`schemas/input.py`**:
```python
from uuid import UUID
from pydantic import BaseModel, Field

class ReviewCommentCreate(BaseModel):
    pull_request_id: UUID
    branch_id: UUID
    path: str = Field(..., max_length=500)
    line_key: str = Field(..., max_length=200)
    body: str
    author: str = Field(..., max_length=200)
    line_number: int | None = None
    side: str | None = None

class ReviewCommentUpdate(BaseModel):
    body: str | None = None
    resolved: bool | None = None
```

**`schemas/output.py`**:
```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class ReviewCommentResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    pull_request_id: UUID
    branch_id: UUID
    path: str
    line_key: str
    line_number: int | None = None
    side: str | None = None
    body: str
    author: str
    external_id: int | None = None
    resolved: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
```

**`service.py`**:
```python
from uuid import UUID
from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import ReviewComment
from .schemas.input import ReviewCommentCreate, ReviewCommentUpdate

class ReviewCommentService(BaseService[ReviewComment, ReviewCommentCreate, ReviewCommentUpdate]):
    model = ReviewComment

    async def list_by_branch(self, db: AsyncSession, branch_id: UUID) -> list[ReviewComment]:
        result = await db.execute(
            select(ReviewComment)
            .where(ReviewComment.branch_id == branch_id)
            .order_by(ReviewComment.created_at)
        )
        return list(result.scalars().all())
```

### Step 2: Database migration

Run: `cd app/backend && just migrate-create "add review_comments table"`

### Step 3: Add comment methods to StackAPI

File: `app/backend/src/molecules/apis/stack_api.py`

Add CRUD methods for comments:
- `create_comment(branch_id, data)` — create + optional GitHub sync
- `list_comments(branch_id)` — list all comments for a branch
- `update_comment(comment_id, data)` — update body/resolved
- `delete_comment(comment_id)` — soft delete

### Step 4: Add GitHubAdapter comment methods

File: `app/backend/src/molecules/providers/github_adapter.py`

```python
async def create_review_comment(
    self, owner: str, repo: str, pr_number: int,
    body: str, path: str, line: int, commit_id: str, side: str = "RIGHT"
) -> dict[str, object]:
    """Create an inline review comment on a PR."""
    response = await self._client.post(
        f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
        json={"body": body, "path": path, "line": line, "side": side, "commit_id": commit_id},
    )
    self._raise_for_status(response)
    return response.json()

async def list_review_comments(
    self, owner: str, repo: str, pr_number: int
) -> list[dict[str, object]]:
    """List all inline review comments on a PR."""
    response = await self._client.get(
        f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
    )
    self._raise_for_status(response)
    return response.json()
```

### Step 5: Add router endpoints

File: `app/backend/src/organisms/api/routers/stacks.py`

- `POST /stacks/{stack_id}/branches/{branch_id}/comments` — create
- `GET /stacks/{stack_id}/branches/{branch_id}/comments` — list
- `PATCH /stacks/{stack_id}/comments/{comment_id}` — update
- `DELETE /stacks/{stack_id}/comments/{comment_id}` — delete

## Frontend Implementation

### Step 6: CommentInput molecule

New file: `app/frontend/src/components/molecules/CommentInput/CommentInput.tsx`

Inline textarea below a diff line. Props: `onSubmit(body)`, `onCancel()`.

### Step 7: useReviewComments hook

New file: `app/frontend/src/hooks/useReviewComments.ts`

```typescript
export function useReviewComments(stackId: string | undefined, branchId: string | undefined) {
  return useQuery({
    queryKey: ["review-comments", stackId, branchId],
    queryFn: () => apiClient.get(`/api/v1/stacks/${stackId}/branches/${branchId}/comments`).then(r => r.data),
    enabled: !!stackId && !!branchId,
  });
}
```

### Step 8: Wire FilesChangedPanel

File: `app/frontend/src/components/organisms/FilesChangedPanel/FilesChangedPanel.tsx`

Replace stub (line 36-38) with:
- `commentingLine` state — which line has the input open
- `handleAddComment` — sets commentingLine
- `handleSubmitComment` — POST to API, invalidate query, close input
- Pass comments data down to DiffHunk

### Step 9: Render comments in DiffHunk

File: `app/frontend/src/components/molecules/DiffHunk/DiffHunk.tsx`

After each DiffLine, if comments exist for that lineKey, render them. If commentingLine matches, render CommentInput.

## Key Architecture Notes

- BasePattern (not EventPattern) — no state machine needed
- Comments reference both branch_id (for fetching) and pull_request_id (for GitHub sync)
- line_key format: `filePath:type:old_num:new_num` (matches DiffHunk's makeLineKey)
- GitHub sync is best-effort: save locally first, then POST to GitHub
- Comments can exist before PR submission (local-only)
