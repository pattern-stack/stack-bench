interface ChatSeparatorProps {
  label?: string;
}

function ChatSeparator({ label }: ChatSeparatorProps) {
  if (!label) {
    return (
      <hr
        className="w-full border-0 h-px my-2"
        style={{ backgroundColor: "var(--chat-border)" }}
      />
    );
  }

  return (
    <div className="flex items-center gap-3 w-full my-2">
      <div
        className="flex-1 h-px"
        style={{ backgroundColor: "var(--chat-border)" }}
      />
      <span
        className="text-xs shrink-0"
        style={{ color: "var(--chat-border)" }}
      >
        {label}
      </span>
      <div
        className="flex-1 h-px"
        style={{ backgroundColor: "var(--chat-border)" }}
      />
    </div>
  );
}

ChatSeparator.displayName = "ChatSeparator";

export { ChatSeparator };
export type { ChatSeparatorProps };
