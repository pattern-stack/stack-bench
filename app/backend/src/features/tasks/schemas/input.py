from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class TaskCreate(BaseModel):
    title: str = PydanticField(..., min_length=1, max_length=500)
    description: str | None = None
    priority: str = PydanticField("none", pattern="^(critical|high|medium|low|none)$")
    issue_type: str = PydanticField("task", pattern="^(story|bug|task|spike|epic)$")
    work_phase: str | None = PydanticField(None, pattern="^(design|build|test|deploy|review)$")
    status_category: str = PydanticField("todo", pattern="^(todo|in_progress|done)$")
    project_id: UUID | None = None
    assignee_id: UUID | None = None
    sprint_id: UUID | None = None
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str = PydanticField("local", pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = PydanticField(None, min_length=1, max_length=500)
    description: str | None = None
    priority: str | None = PydanticField(None, pattern="^(critical|high|medium|low|none)$")
    issue_type: str | None = PydanticField(None, pattern="^(story|bug|task|spike|epic)$")
    work_phase: str | None = PydanticField(None, pattern="^(design|build|test|deploy|review)$")
    status_category: str | None = PydanticField(None, pattern="^(todo|in_progress|done)$")
    state: str | None = PydanticField(None, pattern="^(backlog|ready|in_progress|in_review|done|cancelled)$")
    project_id: UUID | None = None
    assignee_id: UUID | None = None
    sprint_id: UUID | None = None
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str | None = PydanticField(None, pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None
