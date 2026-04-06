from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from molecules.apis.task_api import TaskAPI


@pytest.fixture
def db() -> AsyncMock:
    mock = AsyncMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    return mock


@pytest.fixture
def api(db: AsyncMock) -> TaskAPI:
    return TaskAPI(db)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_job_for_task_creates_conversation(api: TaskAPI) -> None:
    """Creating a job for a task auto-creates a linked conversation."""
    task_id = uuid4()
    job_id = uuid4()
    conv_id = uuid4()

    mock_task = MagicMock()
    mock_task.id = task_id
    mock_task.project_id = uuid4()

    mock_job = MagicMock()
    mock_job.id = job_id
    mock_job.reference_number = "JOB-001"
    mock_job.state = "queued"
    mock_job.task_id = task_id
    mock_job.repo_url = "https://github.com/test/repo"
    mock_job.repo_branch = "main"
    mock_job.issue_number = None
    mock_job.issue_title = None
    mock_job.issue_body = None
    mock_job.current_phase = None
    mock_job.input_text = None
    mock_job.error_message = None
    mock_job.artifacts = {}
    mock_job.gate_decisions = []
    mock_job.job_record_id = None
    mock_job.created_at = MagicMock()
    mock_job.updated_at = MagicMock()

    mock_conv = MagicMock()
    mock_conv.id = conv_id

    mock_data = MagicMock()

    with (
        patch.object(api._task_svc, "get", new_callable=AsyncMock, return_value=mock_task),
        patch.object(api._job_svc, "create", new_callable=AsyncMock, return_value=mock_job),
        patch.object(api._conv_svc, "create", new_callable=AsyncMock, return_value=mock_conv),
        patch.object(api._link_svc, "link_conversation", new_callable=AsyncMock) as mock_link,
    ):
        job_resp, returned_conv_id = await api.create_job_for_task(task_id, mock_data)

    assert returned_conv_id == conv_id
    assert mock_link.call_count == 2  # task link + job link

    # Verify task link
    task_call = mock_link.call_args_list[0]
    assert task_call.kwargs["entity_type"] == "task"
    assert task_call.kwargs["entity_id"] == task_id
    assert task_call.kwargs["relationship_type"] == "execution"

    # Verify job link
    job_call = mock_link.call_args_list[1]
    assert job_call.kwargs["entity_type"] == "job"
    assert job_call.kwargs["entity_id"] == job_id
    assert job_call.kwargs["relationship_type"] == "execution"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_job_for_task_raises_404_when_task_missing(api: TaskAPI) -> None:
    """Raises 404 when the task doesn't exist."""
    from fastapi import HTTPException

    mock_data = MagicMock()

    with (
        patch.object(api._task_svc, "get", new_callable=AsyncMock, return_value=None),
        pytest.raises(HTTPException) as exc_info,
    ):
        await api.create_job_for_task(uuid4(), mock_data)

    assert exc_info.value.status_code == 404
