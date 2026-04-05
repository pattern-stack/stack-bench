import type { ChatRole } from "@/types/chat";

interface ChatRoleIndicatorProps {
  role: ChatRole;
  agentName?: string;
}

const roleConfig: Record<ChatRole, { label: string; color: string }> = {
  user: { label: "you:", color: "var(--chat-user)" },
  assistant: { label: "sb:", color: "var(--chat-agent)" },
  system: { label: "sys:", color: "var(--chat-system)" },
};

function ChatRoleIndicator({ role, agentName }: ChatRoleIndicatorProps) {
  const config = roleConfig[role];
  const label =
    role === "assistant" && agentName ? `${agentName}:` : config.label;

  return (
    <span
      style={{
        display: "inline-block",
        width: 48,
        fontFamily: "var(--font-mono)",
        fontWeight: 700,
        color: config.color,
        flexShrink: 0,
      }}
    >
      {label}
    </span>
  );
}

ChatRoleIndicator.displayName = "ChatRoleIndicator";

export { ChatRoleIndicator };
export type { ChatRoleIndicatorProps };
