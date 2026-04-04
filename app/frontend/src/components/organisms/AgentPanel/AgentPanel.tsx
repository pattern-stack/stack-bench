import { cn } from "@/lib/utils";
import { Icon } from "@/components/atoms/Icon";
import { ChatRoom } from "@/components/organisms/ChatRoom/ChatRoom";

interface AgentPanelProps {
  isOpen: boolean;
  onToggle: () => void;
  selectedLineCount: number;
  branchName: string;
}

function AgentPanel({
  isOpen,
  onToggle,
  selectedLineCount,
  branchName,
}: AgentPanelProps) {
  // Collapsed state
  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className={cn(
          "w-10 flex flex-col items-center gap-3 pt-4 shrink-0",
          "bg-[var(--bg-surface)] border-l border-[var(--border)]",
          "hover:bg-[var(--bg-surface-hover)] transition-colors cursor-pointer"
        )}
      >
        <Icon name="sparkle" size="sm" className="text-[var(--fg-muted)]" />
        <span
          className="text-[var(--fg-muted)] text-xs font-medium tracking-wider"
          style={{ writingMode: "vertical-rl" }}
        >
          Agent
        </span>
      </button>
    );
  }

  // Expanded state
  return (
    <div
      className={cn(
        "w-[360px] shrink-0 flex flex-col",
        "bg-[var(--bg-surface)] border-l border-[var(--border)]"
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[var(--border)]">
        <Icon name="sparkle" size="sm" className="text-[var(--accent-emerald)]" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-[var(--fg-default)]">Agent</div>
          <div className="text-xs text-[var(--fg-muted)] truncate">
            Reviewing {branchName}
          </div>
        </div>
        <button
          onClick={onToggle}
          className="p-1 rounded hover:bg-[var(--bg-surface-hover)] text-[var(--fg-muted)] hover:text-[var(--fg-default)] transition-colors"
        >
          <Icon name="x" size="sm" />
        </button>
      </div>

      {/* Context banner */}
      {selectedLineCount > 0 && (
        <div className="px-3 py-2 bg-[var(--accent-emerald-dim)] text-[var(--accent-emerald)] text-xs font-medium">
          {selectedLineCount} line{selectedLineCount !== 1 ? "s" : ""} selected as context
        </div>
      )}

      {/* ChatRoom fills remaining space */}
      <div className="flex-1 overflow-hidden">
        <ChatRoom
          channel={`agent:${branchName || "default"}`}
          agentName="sb"
          onSendMessage={(text) => {
            // TODO: Wire to POST /api/v1/conversations/{id}/send
            console.log("Send message:", text);
          }}
        />
      </div>
    </div>
  );
}

AgentPanel.displayName = "AgentPanel";

export { AgentPanel };
export type { AgentPanelProps };
