import type { FC } from "react";
import { Badge } from "@/components/atoms/Badge";

interface ChatDiffBlockProps {
  diff: string;
  fileName?: string;
}

function lineColor(line: string): string {
  if (line.startsWith("+")) return "var(--green, #22c55e)";
  if (line.startsWith("-")) return "var(--red, var(--chat-error))";
  return "var(--chat-text-primary)";
}

function lineBg(line: string): string | undefined {
  if (line.startsWith("+")) return "rgba(34,197,94,0.08)";
  if (line.startsWith("-")) return "rgba(239,68,68,0.08)";
  return undefined;
}

const ChatDiffBlock: FC<ChatDiffBlockProps> = ({ diff, fileName }) => {
  const lines = diff.split("\n");

  return (
    <div
      style={{
        borderRadius: 8,
        border: "1px solid var(--chat-border)",
        overflow: "hidden",
        fontFamily: "var(--font-mono)",
        fontSize: 13,
        lineHeight: 1.6,
      }}
    >
      {fileName && (
        <div
          style={{
            padding: "6px 12px",
            borderBottom: "1px solid var(--chat-border)",
            background: "var(--chat-bg-message)",
          }}
        >
          <Badge size="sm">{fileName}</Badge>
        </div>
      )}
      <pre
        style={{
          margin: 0,
          padding: "8px 12px",
          whiteSpace: "pre-wrap",
          wordBreak: "break-all",
          background: "var(--chat-bg-message)",
        }}
      >
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
