import type { ChatMessage } from "@/types/chat";
import { ChatRoleIndicator } from "@/components/atoms/ChatRoleIndicator";
import { ChatTimestamp } from "@/components/atoms/ChatTimestamp";
import { ChatPresenceIndicator } from "@/components/atoms/ChatPresenceIndicator";
import { MessagePartDispatcher } from "@/components/molecules/MessagePartDispatcher";

interface ChatMessageRowProps {
  message: ChatMessage;
  isStreaming?: boolean;
  isWaiting?: boolean;
  agentName?: string;
  showAttribution?: boolean;
}

function ChatMessageRow({
  message,
  isStreaming = false,
  isWaiting = false,
  agentName,
  showAttribution = true,
}: ChatMessageRowProps) {
  const showPresence = isWaiting && message.parts.length === 0;

  return (
    <div>
      {showAttribution && (
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: 8,
            marginBottom: 4,
          }}
        >
          <ChatRoleIndicator role={message.role} agentName={agentName} />
          <ChatTimestamp timestamp={message.timestamp} />
        </div>
      )}
      <div
        style={{
          paddingLeft: 48,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {showPresence ? (
          <ChatPresenceIndicator />
        ) : (
          message.parts.map((part, index) => (
            <MessagePartDispatcher
              key={`${message.id}-${index}`}
              part={part}
              isStreaming={isStreaming}
            />
          ))
        )}
      </div>
    </div>
  );
}

ChatMessageRow.displayName = "ChatMessageRow";

export { ChatMessageRow };
export type { ChatMessageRowProps };
