import type { ChatRole } from "@/types/chat";

interface ChatRoleIndicatorProps {
  role: ChatRole;
  agentName?: string;
}

const roleConfig: Record<ChatRole, { label: string; colorClass: string }> = {
  user: { label: "you:", colorClass: "text-[var(--chat-user)]" },
  assistant: { label: "sb:", colorClass: "text-[var(--chat-agent)]" },
  system: { label: "sys:", colorClass: "text-[var(--chat-system)]" },
};

function ChatRoleIndicator({ role, agentName }: ChatRoleIndicatorProps) {
  const config = roleConfig[role];
  const label =
    role === "assistant" && agentName ? `${agentName}:` : config.label;

  return (
    <span
      className={`inline-block min-w-[var(--chat-label-width)] font-[family-name:var(--font-mono)] font-bold text-[length:var(--chat-font-sm)] shrink-0 ${config.colorClass}`}
    >
      {label}
    </span>
  );
}

ChatRoleIndicator.displayName = "ChatRoleIndicator";

export { ChatRoleIndicator };
export type { ChatRoleIndicatorProps };
