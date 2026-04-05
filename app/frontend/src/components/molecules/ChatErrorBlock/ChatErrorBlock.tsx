import type { FC } from "react";
import { Icon } from "@/components/atoms/Icon";

interface ChatErrorBlockProps {
  message: string;
}

const ChatErrorBlock: FC<ChatErrorBlockProps> = ({ message }) => (
  <div
    style={{
      display: "flex",
      alignItems: "flex-start",
      gap: 8,
      padding: "8px 12px",
      borderRadius: 6,
      background: "var(--chat-bg-message)",
      borderTop: "1px solid var(--chat-error)",
      borderRight: "1px solid var(--chat-error)",
      borderBottom: "1px solid var(--chat-error)",
      borderLeft: "3px solid var(--chat-error)",
      color: "var(--chat-error)",
      fontSize: 13,
      fontFamily: "var(--font-sans)",
      lineHeight: 1.5,
    }}
  >
    <Icon name="alert-triangle" size="sm" style={{ flexShrink: 0, marginTop: 2 }} />
    <span>{message}</span>
  </div>
);

ChatErrorBlock.displayName = "ChatErrorBlock";

export { ChatErrorBlock };
export type { ChatErrorBlockProps };
