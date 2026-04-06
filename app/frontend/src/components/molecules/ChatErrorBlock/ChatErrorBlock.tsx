import type { FC } from "react";
import { Icon } from "@/components/atoms/Icon";

interface ChatErrorBlockProps {
  message: string;
}

const ChatErrorBlock: FC<ChatErrorBlockProps> = ({ message }) => (
  <div className="flex items-start gap-[var(--chat-gap-sm)] px-[var(--chat-gap-md)] py-[var(--chat-gap-sm)] rounded-[var(--chat-radius)] bg-[var(--chat-bg-message)] border border-[var(--chat-error)] border-l-[length:var(--chat-tool-border-width)] border-l-[var(--chat-error)] text-[var(--chat-error)] text-[length:var(--chat-font-sm)] font-[family-name:var(--font-sans)] leading-[1.5]">
    <Icon name="alert-triangle" size="sm" className="shrink-0 mt-0.5" />
    <span>{message}</span>
  </div>
);

ChatErrorBlock.displayName = "ChatErrorBlock";

export { ChatErrorBlock };
export type { ChatErrorBlockProps };
