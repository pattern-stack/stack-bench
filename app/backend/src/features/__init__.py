# Model registry — import all feature models here for alembic discovery
from features.agent_definitions.models import AgentDefinition  # noqa: F401
from features.agent_runs.models import AgentRun  # noqa: F401
from features.branches.models import Branch  # noqa: F401
from features.conversations.models import Conversation  # noqa: F401
from features.jobs.models import Job  # noqa: F401
from features.message_parts.models import MessagePart  # noqa: F401
from features.messages.models import Message  # noqa: F401
from features.projects.models import Project  # noqa: F401
from features.pull_requests.models import PullRequest  # noqa: F401
from features.review_comments.models import ReviewComment  # noqa: F401
from features.role_templates.models import RoleTemplate  # noqa: F401
from features.sprints.models import Sprint  # noqa: F401
from features.stacks.models import Stack  # noqa: F401
from features.task_comments.models import TaskComment  # noqa: F401
from features.task_projects.models import TaskProject  # noqa: F401
from features.task_relations.models import TaskRelation  # noqa: F401
from features.task_tags.models import TaskTag, task_tag_assignments  # noqa: F401
from features.tasks.models import Task  # noqa: F401
from features.tool_calls.models import ToolCall  # noqa: F401
from features.workspaces.models import Workspace  # noqa: F401
