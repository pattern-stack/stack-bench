interface ChatTimestampProps {
  timestamp: string | Date;
}

function formatRelativeTime(timestamp: string | Date): string {
  const date = typeof timestamp === "string" ? new Date(timestamp) : timestamp;
  const now = Date.now();
  const diffMs = now - date.getTime();

  if (diffMs < 0) return "just now";

  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return "just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function ChatTimestamp({ timestamp }: ChatTimestampProps) {
  const date = typeof timestamp === "string" ? new Date(timestamp) : timestamp;

  return (
    <time
      dateTime={date.toISOString()}
      title={date.toLocaleString()}
      style={{
        color: "var(--chat-text-tertiary)",
        fontSize: "0.75rem",
        fontFamily: "var(--font-sans)",
        whiteSpace: "nowrap",
      }}
    >
      {formatRelativeTime(timestamp)}
    </time>
  );
}

ChatTimestamp.displayName = "ChatTimestamp";

export { ChatTimestamp, formatRelativeTime };
export type { ChatTimestampProps };
