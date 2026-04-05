import type { FC } from "react";

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

/** Try to extract a file path from the first line (e.g. "--- a/src/foo.ts") */
function extractFilePath(lines: string[]): string | null {
  for (const line of lines.slice(0, 4)) {
    const match = line.match(/^(?:---|\+\+\+)\s+[ab]\/(.+)/);
    if (match?.[1]) return match[1];
    const diffMatch = line.match(/^diff\s+--git\s+a\/(.+)\s+b\//);
    if (diffMatch?.[1]) return diffMatch[1];
  }
  return null;
}

const ChatDiffBlock: FC<ChatDiffBlockProps> = ({ diff, fileName }) => {
  const lines = diff.split("\n");
  const label = fileName || extractFilePath(lines) || "diff";
  const gutterWidth = `${Math.max(3, String(lines.length).length + 1)}ch`;

  return (
    <div className="rounded-[var(--chat-radius-lg)] border border-[var(--chat-border)] overflow-hidden font-[family-name:var(--font-mono)] text-[length:var(--chat-font-sm)] leading-[1.6]">
      <div className="px-[var(--chat-gap-md)] py-[var(--chat-tool-py)] border-b border-[var(--chat-border)] bg-[var(--chat-bg-message)] flex items-center justify-between">
        <span className="text-[length:var(--chat-font-xs)] text-[var(--chat-text-secondary)] truncate">
          {label}
        </span>
        <span className="text-[length:var(--chat-font-xs)] text-[var(--chat-text-tertiary)] select-none uppercase tracking-[0.5px]">
          diff
        </span>
      </div>
      <pre className="m-0 py-[var(--chat-gap-sm)] whitespace-pre-wrap break-all bg-[var(--chat-bg-message)]">
        {lines.map((line, i) => (
          <div
            key={i}
            className="flex"
            style={{
              color: lineColor(line),
              background: lineBg(line),
            }}
          >
            <span
              className="inline-block text-right pr-[var(--chat-gap-sm)] pl-[var(--chat-gap-sm)] text-[var(--chat-text-quaternary)] select-none shrink-0 border-r border-r-[var(--chat-border)]"
              style={{ width: gutterWidth }}
            >
              {i + 1}
            </span>
            <span className="px-[var(--chat-gap-sm)]">
              {line || "\u00A0"}
            </span>
          </div>
        ))}
      </pre>
    </div>
  );
};

ChatDiffBlock.displayName = "ChatDiffBlock";

export { ChatDiffBlock };
export type { ChatDiffBlockProps };
