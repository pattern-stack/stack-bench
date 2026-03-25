"""Shared conformance tests that any adapter must pass."""

from datetime import UTC, datetime, timedelta

import pytest
from agentic_patterns.core.atoms.exceptions import ConflictError, NotFoundError
from agentic_patterns.core.atoms.protocols import (
    CreateDocumentInput,
    CreateProjectInput,
    CreateSprintInput,
    CreateTagInput,
    CreateTaskInput,
    DocType,
    DocumentFilter,
    Priority,
    ProjectFilter,
    ProjectStatus,
    RelationType,
    SprintStatus,
    StatusCategory,
    TagFilter,
    TagGroup,
    TaskFilter,
    UpdateDocumentInput,
    UpdateProjectInput,
    UpdateSprintInput,
    UpdateTagInput,
    UpdateTaskInput,
    WorkPhase,
)


class AdapterConformanceTests:
    """Base conformance tests for all adapter implementations.

    Subclasses must provide an ``adapter`` fixture.
    """

    # ===== TaskProtocol =====

    @pytest.mark.asyncio
    async def test_task_create_and_get(self, adapter):
        task = await adapter.create_task(CreateTaskInput(title="Test task"))
        assert task.id
        assert task.title == "Test task"
        fetched = await adapter.get_task(task.id)
        assert fetched.title == "Test task"

    @pytest.mark.asyncio
    async def test_task_update(self, adapter):
        task = await adapter.create_task(CreateTaskInput(title="Original"))
        updated = await adapter.update_task(UpdateTaskInput(id=task.id, title="Updated"))
        assert updated.title == "Updated"

    @pytest.mark.asyncio
    async def test_task_delete(self, adapter):
        task = await adapter.create_task(CreateTaskInput(title="To delete"))
        await adapter.delete_task(task.id)
        with pytest.raises(NotFoundError):
            await adapter.get_task(task.id)

    @pytest.mark.asyncio
    async def test_task_list_empty(self, adapter):
        tasks = await adapter.list_tasks()
        assert tasks == []

    @pytest.mark.asyncio
    async def test_task_list_with_filter(self, adapter):
        await adapter.create_task(CreateTaskInput(title="T1", priority=Priority.HIGH))
        await adapter.create_task(CreateTaskInput(title="T2", priority=Priority.LOW))
        # Filter by assignee (should return empty since no assignee set)
        filtered = await adapter.list_tasks(TaskFilter(assignee_id="nobody"))
        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_task_bulk_create(self, adapter):
        tasks = await adapter.create_tasks(
            [
                CreateTaskInput(title="Bulk 1"),
                CreateTaskInput(title="Bulk 2"),
            ]
        )
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_task_get_not_found(self, adapter):
        with pytest.raises(NotFoundError):
            await adapter.get_task("nonexistent")

    @pytest.mark.asyncio
    async def test_task_advance_phase(self, adapter):
        task = await adapter.create_task(
            CreateTaskInput(
                title="Phase test",
                phase=WorkPhase.PLANNING,
                status_category=StatusCategory.DONE,
            )
        )
        advanced = await adapter.advance_phase(task.id)
        assert advanced.phase == WorkPhase.IMPLEMENTATION.value or advanced.phase == WorkPhase.IMPLEMENTATION
        assert advanced.status_category == StatusCategory.TODO.value or advanced.status_category == StatusCategory.TODO

    @pytest.mark.asyncio
    async def test_task_advance_phase_wrong_status(self, adapter):
        task = await adapter.create_task(CreateTaskInput(title="Wrong phase"))
        with pytest.raises(ConflictError):
            await adapter.advance_phase(task.id)

    @pytest.mark.asyncio
    async def test_task_relations(self, adapter):
        t1 = await adapter.create_task(CreateTaskInput(title="Source"))
        t2 = await adapter.create_task(CreateTaskInput(title="Target"))
        await adapter.add_relation(t1.id, t2.id, RelationType.BLOCKS)
        rels = await adapter.get_relations(t1.id)
        assert len(rels) >= 1
        await adapter.remove_relation(t1.id, t2.id, RelationType.BLOCKS)
        rels2 = await adapter.get_relations(t1.id)
        assert len(rels2) == 0

    # ===== CommentProtocol =====

    @pytest.mark.asyncio
    async def test_comment_crud(self, adapter):
        task = await adapter.create_task(CreateTaskInput(title="For comments"))
        comment = await adapter.create_comment(task.id, "Hello world")
        assert comment.body == "Hello world"
        assert comment.issue_id == task.id

        fetched = await adapter.get_comment(comment.id)
        assert fetched.body == "Hello world"

        updated = await adapter.update_comment(comment.id, "Updated body")
        assert updated.body == "Updated body"

        comments = await adapter.list_comments(task.id)
        assert len(comments) == 1

        await adapter.delete_comment(comment.id)
        with pytest.raises(NotFoundError):
            await adapter.get_comment(comment.id)

    @pytest.mark.asyncio
    async def test_comment_reactions(self, adapter):
        task = await adapter.create_task(CreateTaskInput(title="For reactions"))
        comment = await adapter.create_comment(task.id, "React to me")
        reaction = await adapter.add_reaction(comment.id, "\U0001f44d")
        assert reaction.emoji == "\U0001f44d"

        reactions = await adapter.list_reactions(comment.id)
        assert len(reactions) == 1

        await adapter.remove_reaction(comment.id, "\U0001f44d")
        reactions2 = await adapter.list_reactions(comment.id)
        assert len(reactions2) == 0

    # ===== ProjectProtocol =====

    @pytest.mark.asyncio
    async def test_project_crud(self, adapter):
        project = await adapter.create_project(CreateProjectInput(name="Test Project"))
        assert project.name == "Test Project"

        fetched = await adapter.get_project(project.id)
        assert fetched.name == "Test Project"

        updated = await adapter.update_project(UpdateProjectInput(id=project.id, name="Renamed"))
        assert updated.name == "Renamed"

        projects = await adapter.list_projects()
        assert len(projects) == 1

        await adapter.delete_project(project.id)
        with pytest.raises(NotFoundError):
            await adapter.get_project(project.id)

    @pytest.mark.asyncio
    async def test_project_filter(self, adapter):
        await adapter.create_project(CreateProjectInput(name="Active", status_category=ProjectStatus.ACTIVE))
        await adapter.create_project(CreateProjectInput(name="Archived", status_category=ProjectStatus.ARCHIVED))
        active = await adapter.list_projects(ProjectFilter(status_category=ProjectStatus.ACTIVE))
        assert len(active) == 1
        assert active[0].name == "Active"

    @pytest.mark.asyncio
    async def test_project_bulk(self, adapter):
        p1 = await adapter.create_project(CreateProjectInput(name="P1"))
        p2 = await adapter.create_project(CreateProjectInput(name="P2"))
        fetched = await adapter.get_projects([p1.id, p2.id])
        assert len(fetched) == 2

    # ===== SprintProtocol =====

    @pytest.mark.asyncio
    async def test_sprint_crud(self, adapter):
        now = datetime.now(UTC)
        sprint = await adapter.create_sprint(
            CreateSprintInput(
                starts_at=now,
                ends_at=now + timedelta(days=14),
            )
        )
        assert sprint.id

        fetched = await adapter.get_sprint(sprint.id)
        assert fetched.id == sprint.id

        updated = await adapter.update_sprint(UpdateSprintInput(id=sprint.id, name="Sprint 1"))
        assert updated.name == "Sprint 1"

    @pytest.mark.asyncio
    async def test_sprint_active(self, adapter):
        now = datetime.now(UTC)
        await adapter.create_sprint(
            CreateSprintInput(
                starts_at=now,
                ends_at=now + timedelta(days=14),
            )
        )
        # New sprints should be PLANNED status; no active sprint yet
        active = await adapter.get_active_sprint()
        assert active is None or active.status == SprintStatus.ACTIVE or active.status == SprintStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_sprint_issues(self, adapter):
        now = datetime.now(UTC)
        sprint = await adapter.create_sprint(
            CreateSprintInput(
                starts_at=now,
                ends_at=now + timedelta(days=14),
            )
        )
        task = await adapter.create_task(CreateTaskInput(title="Sprint task"))
        await adapter.add_to_sprint(task.id, sprint.id)
        issues = await adapter.get_sprint_issues(sprint.id)
        assert len(issues) == 1

        await adapter.remove_from_sprint(task.id)
        issues2 = await adapter.get_sprint_issues(sprint.id)
        assert len(issues2) == 0

    # ===== TagProtocol =====

    @pytest.mark.asyncio
    async def test_tag_crud(self, adapter):
        tag = await adapter.create_tag(CreateTagInput(name="bug", color="#ff0000"))
        assert tag.name == "bug"

        fetched = await adapter.get_tag(tag.id)
        assert fetched.name == "bug"

        updated = await adapter.update_tag(UpdateTagInput(id=tag.id, name="bugfix"))
        assert updated.name == "bugfix"

        tags = await adapter.list_tags()
        assert len(tags) == 1

        await adapter.delete_tag(tag.id)
        with pytest.raises(NotFoundError):
            await adapter.get_tag(tag.id)

    @pytest.mark.asyncio
    async def test_tag_application(self, adapter):
        task = await adapter.create_task(CreateTaskInput(title="Tagged task"))
        tag = await adapter.create_tag(CreateTagInput(name="important"))

        await adapter.apply_tag(task.id, tag.id)
        entity_tags = await adapter.get_entity_tags(task.id)
        assert len(entity_tags) == 1
        assert entity_tags[0].id == tag.id

        await adapter.remove_tag(task.id, tag.id)
        entity_tags2 = await adapter.get_entity_tags(task.id)
        assert len(entity_tags2) == 0

    @pytest.mark.asyncio
    async def test_tag_bulk(self, adapter):
        t1 = await adapter.create_tag(CreateTagInput(name="t1"))
        t2 = await adapter.create_tag(CreateTagInput(name="t2"))
        task = await adapter.create_task(CreateTaskInput(title="Multi-tag"))

        await adapter.apply_tags(task.id, [t1.id, t2.id])
        tags = await adapter.get_entity_tags(task.id)
        assert len(tags) == 2

        await adapter.set_entity_tags(task.id, [t1.id])
        tags2 = await adapter.get_entity_tags(task.id)
        assert len(tags2) == 1

    @pytest.mark.asyncio
    async def test_tag_filter(self, adapter):
        await adapter.create_tag(CreateTagInput(name="type-bug", group=TagGroup.ISSUE_TYPE))
        await adapter.create_tag(CreateTagInput(name="domain-api", group=TagGroup.DOMAIN))
        filtered = await adapter.list_tags(TagFilter(group=TagGroup.ISSUE_TYPE))
        assert len(filtered) == 1

    # ===== UserProtocol =====

    @pytest.mark.asyncio
    async def test_user_current(self, adapter):
        user = await adapter.get_current_user()
        assert user.id
        assert user.name

    @pytest.mark.asyncio
    async def test_user_get(self, adapter):
        current = await adapter.get_current_user()
        fetched = await adapter.get_user(current.id)
        assert fetched.id == current.id

    @pytest.mark.asyncio
    async def test_user_list(self, adapter):
        users = await adapter.list_users()
        assert len(users) >= 1

    @pytest.mark.asyncio
    async def test_team_operations(self, adapter):
        teams = await adapter.list_teams()
        assert len(teams) >= 1
        team = teams[0]
        fetched_team = await adapter.get_team(team.id)
        assert fetched_team.id == team.id
        members = await adapter.get_team_members(team.id)
        assert len(members) >= 1

    # ===== DocumentProtocol =====

    @pytest.mark.asyncio
    async def test_document_crud(self, adapter):
        doc = await adapter.create_document(
            CreateDocumentInput(
                title="Test Doc",
                content="Hello world",
            )
        )
        assert doc.title == "Test Doc"

        fetched = await adapter.get_document(doc.id)
        assert fetched.content == "Hello world"

        updated = await adapter.update_document(UpdateDocumentInput(id=doc.id, title="Updated Doc"))
        assert updated.title == "Updated Doc"

        docs = await adapter.list_documents()
        assert len(docs) == 1

        await adapter.delete_document(doc.id)
        with pytest.raises(NotFoundError):
            await adapter.get_document(doc.id)

    @pytest.mark.asyncio
    async def test_document_search(self, adapter):
        await adapter.create_document(CreateDocumentInput(title="Alpha spec", content="details about alpha"))
        await adapter.create_document(CreateDocumentInput(title="Beta plan", content="details about beta"))
        results = await adapter.search_documents("alpha")
        assert len(results) == 1
        assert results[0].title == "Alpha spec"

    @pytest.mark.asyncio
    async def test_document_filter(self, adapter):
        await adapter.create_document(CreateDocumentInput(title="D1", content="c1", doc_type=DocType.SPEC))
        await adapter.create_document(CreateDocumentInput(title="D2", content="c2", doc_type=DocType.PRD))
        filtered = await adapter.list_documents(DocumentFilter(doc_type=DocType.SPEC))
        assert len(filtered) == 1
