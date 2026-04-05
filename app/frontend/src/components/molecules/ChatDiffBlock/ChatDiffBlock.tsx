import type { FC } from "react";
import { Badge } from "@/components/atoms/Badge";

interface ChatDiffBlockProps {
  diff: string;
  fileName?: string;
}

function lineColor(line: string): string {
  if (line.startsWith("+")) return "var(--chat-success)";
  if (line.startsWith("-")) return "var(--chat-error)";
  return "var(--chat-text-primary)";
}

function lineBg(line: string): string | undefined {
  if (line.startsWith("+")) return "var(--green-bg)";
  if (line.startsWith("-")) return "var(--red-bg)";
  return undefined;
}

const ChatDiffBlock: FC<ChatDiffBlockProps> = ({ diff, fileName }) => {
  const lines = diff.split("\n");

  return (
    <div className="rounded-[var(--chat-radius-lg)] border border-[var(--chat-border)] overflow-hidden font-[family-name:var(--font-mono)] text-[length:var(--chat-font-sm)] leading-[1.6]">
      {fileName && (
        <div className="px-[var(--chat-gap-md)] py-[var(--chat-tool-py)] border-b border-[var(--chat-border)] bg-[var(--chat-bg-message)]">
          <Badge size="sm">{fileName}</Badge>
        </div>
      )}
      <pre className="m-0 px-[var(--chat-gap-md)] py-[var(--chat-gap-sm)] whitespace-pre-wrap break-all bg-[var(--chat-bg-message)]">
        {lines.map((line, i) => (
          <div
            key={i}
            style={{
              color: lineColor(line),
              background: lineBg(line),
              padding: "0 4px",
              marginLeft: -4,
              marginRight: -4,
            }}
          >
            {line || "\u00A0"}
          </div>
        ))}
      </pre>
    </div>
  );
};

ChatDiffBlock.displayName = "ChatDiffBlock";

export { ChatDiffBlock };
export type { ChatDiffBlockProps };
