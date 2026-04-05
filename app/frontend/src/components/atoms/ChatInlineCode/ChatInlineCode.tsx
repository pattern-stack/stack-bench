import type { ReactNode } from "react";

interface ChatInlineCodeProps {
  children: ReactNode;
}

function ChatInlineCode({ children }: ChatInlineCodeProps) {
  return (
    <code
      className="inline rounded-[3px] px-1.5 py-0.5 text-[0.9em] leading-none"
      style={{
        fontFamily: "var(--font-mono)",
        backgroundColor: "var(--chat-bg-message)",
        color: "var(--chat-tool)",
      }}
    >
      {children}
    </code>
  );
}

ChatInlineCode.displayName = "ChatInlineCode";

export { ChatInlineCode };
export type { ChatInlineCodeProps };
