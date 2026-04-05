import { useState, type FC } from "react";

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

  const label = isStreaming ? "thinking..." : "thought";

  return (
    <div className="text-[var(--chat-text-tertiary)] opacity-75 text-[length:var(--chat-font-sm)] font-[family-name:var(--font-sans)]">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        style={{
          all: "unset",
          cursor: "pointer",
          display: "inline-flex",
          alignItems: "center",
          gap: "var(--chat-gap-xs)",
          color: "var(--chat-text-tertiary)",
          fontStyle: "italic",
          fontSize: "var(--chat-font-sm)",
        }}
      >
        <span
          className="inline-block transition-transform duration-[120ms] ease-in-out"
          style={{
            transform: expanded ? "rotate(90deg)" : "rotate(0deg)",
          }}
        >
          &#9654;
        </span>
        <span>{label}</span>
        {!expanded && (
          <span className="opacity-60 not-italic">{preview}</span>
        )}
      </button>

      {expanded && (
        <div className="mt-[var(--chat-tool-py)] px-[var(--chat-gap-md)] py-[var(--chat-gap-sm)] bg-[var(--chat-bg-message)] border border-[var(--chat-border)] rounded-[var(--chat-radius)] whitespace-pre-wrap font-[family-name:var(--font-sans)] text-[length:var(--chat-font-sm)] leading-[1.5] text-[var(--chat-text-tertiary)]">
          {content}
        </div>
      )}
    </div>
  );
};

ChatThinkingBlock.displayName = "ChatThinkingBlock";

export { ChatThinkingBlock };
export type { ChatThinkingBlockProps };
