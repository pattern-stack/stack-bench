import type { ReactNode } from "react";

interface ChatInlineCodeProps {
  children: ReactNode;
}

function ChatInlineCode({ children }: ChatInlineCodeProps) {
  return (
    <code className="inline rounded-[3px] px-1.5 py-0.5 text-[0.9em] leading-none font-[family-name:var(--font-mono)] bg-[var(--chat-bg-message)] text-[var(--chat-tool)]">
      {children}
    </code>
  );
}

ChatInlineCode.displayName = "ChatInlineCode";

export { ChatInlineCode };
export type { ChatInlineCodeProps };
