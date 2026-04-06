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

  const statusColorClass =
    state === "complete"
      ? "text-[var(--chat-success)]"
      : state === "failed"
        ? "text-[var(--chat-error)]"
        : "text-[var(--chat-text-secondary)]";

  return (
    <div className="border-l-[length:var(--chat-tool-border-width)] border-l-[var(--chat-tool)] rounded-[var(--chat-radius)] my-[var(--chat-tool-py)]">
      {/* Header */}
      <button
        type="button"
        onClick={() => hasBody && setExpanded((prev) => !prev)}
        className={`flex items-center gap-[var(--chat-gap-sm)] w-full px-[var(--chat-tool-px)] py-[var(--chat-tool-py)] bg-transparent border-none text-left font-[family-name:var(--font-sans)] text-[length:var(--chat-font-sm)] text-[var(--chat-text-primary)] ${hasBody ? "cursor-pointer" : "cursor-default"}`}
      >
        {/* Status icon */}
        {state === "running" && <ChatSpinner size="sm" />}
        {state === "complete" && (
          <Icon
            name="check"
            size="sm"
            className="text-[var(--chat-success)]"
          />
        )}
        {state === "failed" && (
          <Icon
            name="x"
            size="sm"
            className="text-[var(--chat-error)]"
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
        <span className={`${statusColorClass} text-[length:var(--chat-font-xs)]`}>
          {state === "running" && "running"}
          {state === "complete" && "done"}
          {state === "failed" && "failed"}
        </span>

        {/* Collapsed input preview */}
        {!expanded && input && (
          <span className="text-[var(--chat-text-tertiary)] text-[length:var(--chat-font-xs)] font-[family-name:var(--font-mono)] truncate">
            — {input.length > 60 ? input.slice(0, 60) + "..." : input}
          </span>
        )}

        {/* Expand chevron */}
        {hasBody && (
          <Icon
            name={expanded ? "chevron-down" : "chevron-right"}
            size="xs"
            className="text-[var(--chat-text-secondary)] ml-auto shrink-0"
          />
        )}
      </button>

      {/* Expandable body */}
      {expanded && hasBody && (
        <div className="px-[var(--chat-tool-px)] pb-[var(--chat-gap-sm)]">
          {error && (
            <div className="text-[var(--chat-error)] font-[family-name:var(--font-mono)] text-[length:var(--chat-font-sm)] py-[var(--chat-tool-py)] whitespace-pre-wrap">
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
