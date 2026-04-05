import { useState, useEffect, type FC } from "react";
import { highlightCode } from "@/lib/shiki";

export interface ChatCodeBlockProps {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
}

const ChatCodeBlock: FC<ChatCodeBlockProps> = ({
  code,
  language,
  showLineNumbers = false,
}) => {
  const [highlightedLines, setHighlightedLines] = useState<string[] | null>(
    null
  );

  useEffect(() => {
    if (!language) return;

    let cancelled = false;
    highlightCode(code, language).then((lines) => {
      if (!cancelled) setHighlightedLines(lines);
    });
    return () => {
      cancelled = true;
    };
  }, [code, language]);

  const lines = code.split("\n");

  return (
    <div className="border-l-[length:var(--chat-tool-border-width)] border-l-[var(--chat-tool)] bg-[var(--chat-bg-message)] rounded-[var(--chat-radius)] my-[var(--chat-gap-sm)] relative font-[family-name:var(--font-mono)] text-[length:var(--chat-font-sm)] leading-[1.5]">
      {language && (
        <span className="absolute top-[var(--chat-tool-py)] right-[var(--chat-tool-px)] text-[length:var(--chat-font-xs)] text-[var(--chat-text-tertiary)] select-none uppercase tracking-[0.5px]">
          {language}
        </span>
      )}
      <pre className="m-0 px-[var(--chat-gap-lg)] py-[var(--chat-gap-md)] overflow-x-auto text-[var(--chat-text-primary)]">
        <code>
          {lines.map((line, i) => (
            <div key={i} className="flex">
              {showLineNumbers && (
                <span
                  className="inline-block text-right mr-[var(--chat-gap-lg)] text-[var(--chat-text-quaternary)] select-none shrink-0"
                  style={{ width: `${String(lines.length).length + 1}ch` }}
                >
                  {i + 1}
                </span>
              )}
              {highlightedLines ? (
                <span
                  dangerouslySetInnerHTML={{
                    __html: highlightedLines[i] || "",
                  }}
                />
              ) : (
                <span>{line}</span>
              )}
            </div>
          ))}
        </code>
      </pre>
    </div>
  );
};

ChatCodeBlock.displayName = "ChatCodeBlock";

export { ChatCodeBlock };
