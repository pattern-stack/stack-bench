import { useState, type FC } from "react";
import { ChatSpinner } from "@/components/atoms/ChatSpinner";
import { ChatCodeBlock } from "@/components/atoms/ChatCodeBlock";
import { Badge } from "@/components/atoms/Badge";
import { Icon } from "@/components/atoms/Icon";
import type { ToolCallState, DisplayType } from "@/types/chat";

interface ChatToolCallBlockProps {
  toolName: string;
  state: ToolCallState;
  displayType?: DisplayType;
  input?: string;
  output?: string;
  error?: string;
}

const languageForDisplay: Record<DisplayType, string | undefined> = {
  diff: "diff",
  code: undefined,
  bash: "bash",
  generic: undefined,
};

const ChatToolCallBlock: FC<ChatToolCallBlockProps> = ({
  toolName,
  state,
  displayType = "generic",
  input,
  output,
  error,
}) => {
  const [expanded, setExpanded] = useState(state === "running");

  const hasBody = !!(input || output || error);

  return (
    <div
      style={{
        borderLeft: "3px solid var(--chat-tool)",
        borderRadius: 4,
        margin: "6px 0",
      }}
    >
      {/* Header */}
      <button
        type="button"
        onClick={() => hasBody && setExpanded((prev) => !prev)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          padding: "6px 10px",
          background: "none",
          border: "none",
          cursor: hasBody ? "pointer" : "default",
          fontFamily: "var(--font-sans)",
          fontSize: 13,
          color: "var(--chat-text-primary)",
          textAlign: "left",
        }}
      >
        {/* Status icon */}
        {state === "running" && <ChatSpinner size="sm" />}
        {state === "complete" && (
          <Icon
            name="check"
            size="sm"
            style={{ color: "var(--chat-success)" }}
          />
        )}
        {state === "failed" && (
          <Icon
            name="x"
            size="sm"
            style={{ color: "var(--chat-error)" }}
          />
        )}

        {/* Tool name badge */}
        <Badge
          size="sm"
          className="bg-[var(--chat-tool)]/10 text-[var(--chat-tool)] border-[var(--chat-tool)]/20"
        >
          {toolName}
        </Badge>

        {/* Status text */}
        <span
          style={{
            color:
              state === "complete"
                ? "var(--chat-success)"
                : state === "failed"
                  ? "var(--chat-error)"
                  : "var(--chat-text-secondary)",
            fontSize: 12,
          }}
        >
          {state === "running" && "running"}
          {state === "complete" && "done"}
          {state === "failed" && "failed"}
        </span>

        {/* Expand chevron */}
        {hasBody && (
          <Icon
            name={expanded ? "chevron-down" : "chevron-right"}
            size="xs"
            style={{
              color: "var(--chat-text-secondary)",
              marginLeft: "auto",
            }}
          />
        )}
      </button>

      {/* Expandable body */}
      {expanded && hasBody && (
        <div style={{ padding: "0 10px 8px" }}>
          {error && (
            <div
              style={{
                color: "var(--chat-error)",
                fontFamily: "var(--font-mono)",
                fontSize: 13,
                padding: "6px 0",
                whiteSpace: "pre-wrap",
              }}
            >
              {error}
            </div>
          )}
          {input && (
            <ChatCodeBlock
              code={input}
              language={languageForDisplay[displayType]}
            />
          )}
          {output && (
            <ChatCodeBlock
              code={output}
              language={languageForDisplay[displayType]}
            />
          )}
        </div>
      )}
    </div>
  );
};

ChatToolCallBlock.displayName = "ChatToolCallBlock";

export { ChatToolCallBlock };
export type { ChatToolCallBlockProps };
