interface ChatPresenceIndicatorProps {
  label?: string;
}

function ChatPresenceIndicator({ label }: ChatPresenceIndicatorProps) {
  return (
    <>
      <style>{`
        @keyframes chat-presence-bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30% { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>
      <span
        className="inline-flex items-center gap-1"
        role="status"
        aria-label={label ?? "Agent is typing"}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            style={{
              display: "inline-block",
              width: 6,
              height: 6,
              borderRadius: "50%",
              backgroundColor: "var(--chat-running)",
              animation: `chat-presence-bounce 1.2s ease-in-out ${i * 0.15}s infinite`,
            }}
          />
        ))}
      </span>
    </>
  );
}

ChatPresenceIndicator.displayName = "ChatPresenceIndicator";

export { ChatPresenceIndicator };
export type { ChatPresenceIndicatorProps };
