interface ChatSpinnerProps {
  label?: string;
  size?: "sm" | "md";
}

const sizeStyles = {
  sm: { width: 14, height: 14, borderWidth: 2 },
  md: { width: 20, height: 20, borderWidth: 2.5 },
} as const;

function ChatSpinner({ label, size = "md" }: ChatSpinnerProps) {
  const s = sizeStyles[size];

  return (
    <>
      <style>{`
        @keyframes chat-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
      <span
        className="inline-flex items-center gap-1.5"
        role="status"
        aria-label={label ?? "Loading"}
      >
        <span
          style={{
            display: "inline-block",
            width: s.width,
            height: s.height,
            borderRadius: "50%",
            borderWidth: s.borderWidth,
            borderStyle: "solid",
            borderColor: "var(--chat-running)",
            borderTopColor: "transparent",
            animation: "chat-spin 0.7s linear infinite",
            flexShrink: 0,
          }}
        />
        {label && (
          <span
            className={`text-[var(--chat-text-secondary)] font-[family-name:var(--font-sans)] ${size === "sm" ? "text-[length:var(--chat-font-xs)]" : "text-[length:var(--chat-font-sm)]"}`}
          >
            {label}
          </span>
        )}
      </span>
    </>
  );
}

ChatSpinner.displayName = "ChatSpinner";

export { ChatSpinner };
export type { ChatSpinnerProps };
