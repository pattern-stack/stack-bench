# Model registry — import all feature models here for alembic discovery
from features.conversations.models import Conversation  # noqa: F401
from features.message_parts.models import MessagePart  # noqa: F401
from features.messages.models import Message  # noqa: F401
from features.tool_calls.models import ToolCall  # noqa: F401
