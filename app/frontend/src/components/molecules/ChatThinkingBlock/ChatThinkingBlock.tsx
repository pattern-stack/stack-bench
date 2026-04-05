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
    <div
      style={{
        color: "var(--chat-text-tertiary)",
        opacity: 0.75,
        fontSize: 13,
        fontFamily: "var(--font-sans)",
      }}
    >
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        style={{
          all: "unset",
          cursor: "pointer",
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          color: "var(--chat-text-tertiary)",
          fontStyle: "italic",
          fontSize: 13,
        }}
      >
        <span
          style={{
            display: "inline-block",
            transition: "transform 120ms ease",
            transform: expanded ? "rotate(90deg)" : "rotate(0deg)",
          }}
        >
          &#9654;
        </span>
        <span>{label}</span>
        {!expanded && (
          <span style={{ opacity: 0.6, fontStyle: "normal" }}>{preview}</span>
        )}
      </button>

      {expanded && (
        <div
          style={{
            marginTop: 6,
            padding: "8px 12px",
            background: "var(--chat-bg-message)",
            border: "1px solid var(--chat-border)",
            borderRadius: 6,
            whiteSpace: "pre-wrap",
            fontFamily: "var(--font-sans)",
            fontSize: 13,
            lineHeight: 1.5,
            color: "var(--chat-text-tertiary)",
          }}
        >
          {content}
        </div>
      )}
    </div>
  );
};

ChatThinkingBlock.displayName = "ChatThinkingBlock";

export { ChatThinkingBlock };
export type { ChatThinkingBlockProps };
