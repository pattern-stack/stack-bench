import type { ReactNode } from "react";

import type { ChatRole } from "@/types/chat";
import { ChatRoleIndicator } from "@/components/atoms/ChatRoleIndicator";
import { ChatTimestamp } from "@/components/atoms/ChatTimestamp";
import { ChatSeparator } from "@/components/atoms/ChatSeparator";

interface ChatMessageGroupProps {
  role: ChatRole;
  agentName?: string;
  timestamp: string | Date;
  showDateSeparator?: boolean;
  dateSeparatorLabel?: string;
  children: ReactNode;
}

function ChatMessageGroup({
  role,
  agentName,
  timestamp,
  showDateSeparator = false,
  dateSeparatorLabel,
  children,
}: ChatMessageGroupProps) {
  return (
    <div>
      {showDateSeparator && <ChatSeparator label={dateSeparatorLabel} />}
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 8,
          marginBottom: 4,
        }}
      >
        <ChatRoleIndicator role={role} agentName={agentName} />
        <ChatTimestamp timestamp={timestamp} />
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 4,
        }}
      >
        {children}
      </div>
    </div>
  );
}

ChatMessageGroup.displayName = "ChatMessageGroup";

export { ChatMessageGroup };
export type { ChatMessageGroupProps };
