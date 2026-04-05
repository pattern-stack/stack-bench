interface ChatNoticeProps {
  message: string;
  variant?: "info" | "warning" | "error";
}

const variantColors = {
  info: "var(--chat-info)",
  warning: "var(--chat-warning)",
  error: "var(--chat-error)",
} as const;

function ChatNotice({ message, variant = "info" }: ChatNoticeProps) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        padding: "4px 0",
      }}
    >
      <span
        style={{
          fontSize: "0.8rem",
          lineHeight: 1.4,
          color: variantColors[variant],
          opacity: 0.7,
          fontFamily: "var(--font-sans)",
        }}
      >
        {message}
      </span>
    </div>
  );
}

ChatNotice.displayName = "ChatNotice";

export { ChatNotice };
export type { ChatNoticeProps };
