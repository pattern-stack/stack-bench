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
      <div className="flex items-baseline gap-[var(--chat-gap-sm)] mb-[var(--chat-gap-xs)]">
        <ChatRoleIndicator role={role} agentName={agentName} />
        <ChatTimestamp timestamp={timestamp} />
      </div>
      <div className="flex flex-col gap-[var(--chat-gap-xs)]">
        {children}
      </div>
    </div>
  );
}

ChatMessageGroup.displayName = "ChatMessageGroup";

export { ChatMessageGroup };
export type { ChatMessageGroupProps };
