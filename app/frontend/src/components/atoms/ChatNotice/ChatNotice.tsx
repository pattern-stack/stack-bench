interface ChatNoticeProps {
  message: string;
  variant?: "info" | "warning" | "error";
}

const variantClasses = {
  info: "text-[var(--chat-info)]",
  warning: "text-[var(--chat-warning)]",
  error: "text-[var(--chat-error)]",
} as const;

function ChatNotice({ message, variant = "info" }: ChatNoticeProps) {
  return (
    <div className="flex justify-center py-[var(--chat-gap-xs)]">
      <span
        className={`text-[length:var(--chat-font-xs)] leading-[1.4] opacity-70 font-[family-name:var(--font-sans)] ${variantClasses[variant]}`}
      >
        {message}
      </span>
    </div>
  );
}

ChatNotice.displayName = "ChatNotice";

export { ChatNotice };
export type { ChatNoticeProps };
