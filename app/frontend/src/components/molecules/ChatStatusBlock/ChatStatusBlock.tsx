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
  <span
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
    }}
  >
    {isActive && <ChatSpinner size="sm" />}
    <span
      style={{
        color: "var(--chat-text-primary)",
        fontFamily: "var(--font-sans)",
        fontSize: 13,
        fontWeight: 500,
      }}
    >
      {label}
    </span>
    {elapsed && <Badge size="sm">{elapsed}</Badge>}
    {count && <Badge size="sm">{count}</Badge>}
  </span>
);

ChatStatusBlock.displayName = "ChatStatusBlock";

export { ChatStatusBlock };
export type { ChatStatusBlockProps };
