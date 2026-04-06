"""Tests for task and job REST API routers."""

from __future__ import annotations

from uuid import uuid4

import pytest

from organisms.api.app import app as live_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(db):
    """Create a user for FK constraints."""
    from pattern_stack.features.users.models import User

    user = User(
        first_name="Test",
        last_name="User",
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_project(db):
    """Create a project with required fields for tests."""
    from features.projects import ProjectCreate, ProjectService

    user = await _create_user(db)
    project_service = ProjectService()
    project = await project_service.create(
        db,
        ProjectCreate(
            name=f"test-project-{uuid4().hex[:8]}",
            owner_id=user.id,
            github_repo="https://github.com/test-org/test-repo",
        ),
    )
    await db.flush()
    return project


async def _create_task(db, project_id, title="Test Task"):
    """Create a task via the service."""
    from features.tasks import TaskCreate, TaskService

    task_service = TaskService()
    task = await task_service.create(
        db,
        TaskCreate(title=title, project_id=project_id),
    )
    await db.flush()
    return task


async def _create_job(db, task_id=None):
    """Create a job optionally linked to a task."""
    from features.jobs import JobCreate, JobService

    job_service = JobService()
    job = await job_service.create(
        db,
        JobCreate(
            task_id=task_id,
            repo_url="https://github.com/test/repo",
            repo_branch="main",
        ),
    )
    await db.flush()
    return job


async def _create_agent_run(db, job_id, phase="builder", runner_type="claude"):
    """Create an agent run linked to a job."""
    from features.agent_runs import AgentRunCreate, AgentRunService

    run_service = AgentRunService()
    run = await run_service.create(
        db,
        AgentRunCreate(job_id=job_id, phase=phase, runner_type=runner_type),
    )
    await db.flush()
    return run


# ---------------------------------------------------------------------------
# Route Registration (unit tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_task_routes_registered() -> None:
    """Verify /tasks routes exist on the app."""
    routes = [getattr(r, "path", str(r)) for r in live_app.routes]
    assert any("/tasks" in r for r in routes)


@pytest.mark.unit
def test_task_detail_route_registered() -> None:
    """Verify /tasks/{task_id}/detail route exists."""
    routes = [getattr(r, "path", str(r)) for r in live_app.routes]
    assert any("/tasks/{task_id}/detail" in r for r in routes)


@pytest.mark.unit
def test_job_routes_registered() -> None:
    """Verify /jobs routes exist on the app."""
    routes = [getattr(r, "path", str(r)) for r in live_app.routes]
    assert any("/jobs" in r for r in routes)


# ---------------------------------------------------------------------------
# Task CRUD (integration tests)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_create_task(client, db) -> None:
    """POST /tasks/ creates a task with 201."""
    project = await _create_project(db)
    await db.commit()

    response = client.post(
        "/api/v1/tasks/",
        json={
            "title": "Build dashboard",
            "project_id": str(project.id),
            "priority": "high",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Build dashboard"
    assert data["priority"] == "high"
    assert data["state"] == "backlog"
    assert data["project_id"] == str(project.id)


@pytest.mark.integration
async def test_create_task_minimal(client, db) -> None:
    """POST /tasks/ with only title succeeds."""
    response = client.post(
        "/api/v1/tasks/",
        json={"title": "Minimal task"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Minimal task"
    assert data["priority"] == "none"
    assert data["issue_type"] == "task"


@pytest.mark.integration
async def test_list_tasks_by_project(client, db) -> None:
    """GET /tasks/?project_id= returns tasks for that project."""
    project = await _create_project(db)
    await _create_task(db, project.id, title="Task A")
    await _create_task(db, project.id, title="Task B")
    await db.commit()

    response = client.get(f"/api/v1/tasks/?project_id={project.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = {t["title"] for t in data}
    assert "Task A" in titles
    assert "Task B" in titles


@pytest.mark.integration
async def test_list_tasks_requires_project_id(client) -> None:
    """GET /tasks/ without project_id returns 422."""
    response = client.get("/api/v1/tasks/")
    assert response.status_code == 422


@pytest.mark.integration
async def test_get_task(client, db) -> None:
    """GET /tasks/{task_id} returns the task."""
    project = await _create_project(db)
    task = await _create_task(db, project.id, title="Get me")
    await db.commit()

    response = client.get(f"/api/v1/tasks/{task.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Get me"
    assert data["id"] == str(task.id)


@pytest.mark.integration
async def test_get_task_not_found(client) -> None:
    """GET /tasks/{unknown_id} returns 404."""
    response = client.get(f"/api/v1/tasks/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.integration
async def test_update_task_fields(client, db) -> None:
    """PATCH /tasks/{task_id} updates title and priority."""
    project = await _create_project(db)
    task = await _create_task(db, project.id, title="Before")
    await db.commit()

    response = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"title": "After", "priority": "critical"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "After"
    assert data["priority"] == "critical"


@pytest.mark.integration
async def test_update_task_state_transition(client, db) -> None:
    """PATCH /tasks/{task_id} with state transitions the task."""
    project = await _create_project(db)
    task = await _create_task(db, project.id, title="Transition me")
    await db.commit()

    response = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"state": "ready"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "ready"


@pytest.mark.integration
async def test_delete_task(client, db) -> None:
    """DELETE /tasks/{task_id} soft-deletes with 204."""
    project = await _create_project(db)
    task = await _create_task(db, project.id, title="Delete me")
    await db.commit()

    response = client.delete(f"/api/v1/tasks/{task.id}")
    assert response.status_code == 204

    # Should not appear in list anymore
    response = client.get(f"/api/v1/tasks/{task.id}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Task Detail (integration tests)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_task_detail_no_job(client, db) -> None:
    """GET /tasks/{task_id}/detail returns task with null job and empty runs."""
    project = await _create_project(db)
    task = await _create_task(db, project.id, title="Detail no job")
    await db.commit()

    response = client.get(f"/api/v1/tasks/{task.id}/detail")
    assert response.status_code == 200
    data = response.json()
    assert data["task"]["title"] == "Detail no job"
    assert data["job"] is None
    assert data["agent_runs"] == []


@pytest.mark.integration
async def test_task_detail_with_job_and_runs(client, db) -> None:
    """GET /tasks/{task_id}/detail returns task with job and agent runs."""
    project = await _create_project(db)
    task = await _create_task(db, project.id, title="Detail with job")
    job = await _create_job(db, task_id=task.id)
    await _create_agent_run(db, job.id, phase="architect", runner_type="claude")
    await _create_agent_run(db, job.id, phase="builder", runner_type="claude")
    await db.commit()

    response = client.get(f"/api/v1/tasks/{task.id}/detail")
    assert response.status_code == 200
    data = response.json()
    assert data["task"]["title"] == "Detail with job"
    assert data["job"] is not None
    assert data["job"]["id"] == str(job.id)
    assert len(data["agent_runs"]) == 2
    phases = [r["phase"] for r in data["agent_runs"]]
    assert "architect" in phases
    assert "builder" in phases


@pytest.mark.integration
async def test_task_detail_not_found(client) -> None:
    """GET /tasks/{unknown_id}/detail returns 404."""
    response = client.get(f"/api/v1/tasks/{uuid4()}/detail")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Job endpoints (integration tests)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_list_jobs_for_task(client, db) -> None:
    """GET /jobs/?task_id= returns jobs linked to the task."""
    project = await _create_project(db)
    task = await _create_task(db, project.id, title="Job task")
    await _create_job(db, task_id=task.id)
    await _create_job(db, task_id=task.id)
    await db.commit()

    response = client.get(f"/api/v1/jobs/?task_id={task.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.integration
async def test_list_jobs_requires_task_id(client) -> None:
    """GET /jobs/ without task_id returns 422."""
    response = client.get("/api/v1/jobs/")
    assert response.status_code == 422


@pytest.mark.integration
async def test_get_job_with_runs(client, db) -> None:
    """GET /jobs/{job_id} returns job with its agent runs."""
    project = await _create_project(db)
    task = await _create_task(db, project.id, title="Job detail task")
    job = await _create_job(db, task_id=task.id)
    await _create_agent_run(db, job.id, phase="validator", runner_type="claude")
    await db.commit()

    response = client.get(f"/api/v1/jobs/{job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job"]["id"] == str(job.id)
    assert data["job"]["task_id"] == str(task.id)
    assert len(data["agent_runs"]) == 1
    assert data["agent_runs"][0]["phase"] == "validator"


@pytest.mark.integration
async def test_get_job_not_found(client) -> None:
    """GET /jobs/{unknown_id} returns 404."""
    response = client.get(f"/api/v1/jobs/{uuid4()}")
    assert response.status_code == 404
