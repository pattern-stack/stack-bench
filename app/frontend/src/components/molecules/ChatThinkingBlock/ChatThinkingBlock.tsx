import { useState, type FC } from "react";
import { Icon } from "@/components/atoms/Icon";

interface ChatThinkingBlockProps {
  content: string;
  isStreaming?: boolean;
}

const PREVIEW_LENGTH = 80;

const ChatThinkingBlock: FC<ChatThinkingBlockProps> = ({
  content,
  isStreaming = false,
}) => {
  const [expanded, setExpanded] = useState(false);

  const preview =
    content.length > PREVIEW_LENGTH
      ? content.slice(0, PREVIEW_LENGTH) + "..."
      : content;

  const label = isStreaming ? "Thinking..." : "Thought";

  return (
    <div className="text-[length:var(--chat-font-sm)] font-[family-name:var(--font-sans)]">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex items-center gap-[var(--chat-gap-sm)] w-full px-[var(--chat-tool-px)] py-[var(--chat-tool-py)] bg-[var(--chat-bg-message)] border border-[var(--chat-border)] rounded-[var(--chat-radius)] cursor-pointer text-[length:var(--chat-font-sm)] font-[family-name:var(--font-sans)]"
      >
        <Icon
          name="sparkles"
          size="sm"
          className="text-[var(--chat-tool)] shrink-0"
        />
        <span className="text-[var(--chat-text-secondary)] font-medium">
          {label}
        </span>
        {!expanded && (
          <span className="text-[var(--chat-text-tertiary)] truncate">
            {preview}
          </span>
        )}
        <Icon
          name={expanded ? "chevron-down" : "chevron-right"}
          size="xs"
          className="text-[var(--chat-text-secondary)] ml-auto shrink-0"
        />
      </button>

      {expanded && (
        <div className="mt-[var(--chat-gap-xs)] px-[var(--chat-gap-md)] py-[var(--chat-gap-sm)] bg-[var(--chat-bg-message)] border border-[var(--chat-border)] rounded-[var(--chat-radius)] whitespace-pre-wrap font-[family-name:var(--font-sans)] text-[length:var(--chat-font-sm)] leading-[1.5] text-[var(--chat-text-secondary)]">
          {content}
        </div>
      )}
    </div>
  );
};

ChatThinkingBlock.displayName = "ChatThinkingBlock";

export { ChatThinkingBlock };
export type { ChatThinkingBlockProps };
