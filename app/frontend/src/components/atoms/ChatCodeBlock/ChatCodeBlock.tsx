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
    <div
      style={{
        borderLeft: "3px solid var(--chat-tool)",
        background: "var(--chat-bg-message)",
        borderRadius: "4px",
        margin: "8px 0",
        position: "relative",
        fontFamily: "var(--font-mono)",
        fontSize: "13px",
        lineHeight: "1.5",
      }}
    >
      {language && (
        <span
          style={{
            position: "absolute",
            top: "6px",
            right: "10px",
            fontSize: "11px",
            color: "var(--chat-text-tertiary)",
            userSelect: "none",
            textTransform: "uppercase",
            letterSpacing: "0.5px",
          }}
        >
          {language}
        </span>
      )}
      <pre
        style={{
          margin: 0,
          padding: "12px 16px",
          overflowX: "auto",
          color: "var(--chat-text-primary)",
        }}
      >
        <code>
          {lines.map((line, i) => (
            <div key={i} style={{ display: "flex" }}>
              {showLineNumbers && (
                <span
                  style={{
                    display: "inline-block",
                    width: `${String(lines.length).length + 1}ch`,
                    textAlign: "right",
                    marginRight: "16px",
                    color: "var(--chat-text-quaternary)",
                    userSelect: "none",
                    flexShrink: 0,
                  }}
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
