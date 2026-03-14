# Model registry — import all feature models here for alembic discovery
from features.agent_definitions.models import AgentDefinition  # noqa: F401
from features.agent_runs.models import AgentRun  # noqa: F401
from features.conversations.models import Conversation  # noqa: F401
from features.jobs.models import Job  # noqa: F401
from features.message_parts.models import MessagePart  # noqa: F401
from features.messages.models import Message  # noqa: F401
from features.role_templates.models import RoleTemplate  # noqa: F401
from features.tool_calls.models import ToolCall  # noqa: F401
