import type { FC } from "react";
import { ChatSpinner } from "@/components/atoms/ChatSpinner";
import { Badge } from "@/components/atoms/Badge";

interface ChatStatusBlockProps {
  label: string;
  elapsed?: string;
  count?: string;
  isActive?: boolean;
}

const ChatStatusBlock: FC<ChatStatusBlockProps> = ({
  label,
  elapsed,
  count,
  isActive = false,
}) => (
  <span className="inline-flex items-center gap-[var(--chat-gap-sm)]">
    {isActive && <ChatSpinner size="sm" />}
    <span className="text-[var(--chat-text-primary)] font-[family-name:var(--font-sans)] text-[length:var(--chat-font-sm)] font-medium">
      {label}
    </span>
    {elapsed && <Badge size="sm">{elapsed}</Badge>}
    {count && <Badge size="sm">{count}</Badge>}
  </span>
);

ChatStatusBlock.displayName = "ChatStatusBlock";

export { ChatStatusBlock };
export type { ChatStatusBlockProps };
