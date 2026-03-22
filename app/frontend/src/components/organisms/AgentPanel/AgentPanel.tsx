import { useState, useRef, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Icon } from "@/components/atoms/Icon";

type MessageRole = "system" | "user" | "assistant";

interface AgentMessage {
  role: MessageRole;
  content: string;
}

interface AgentPanelProps {
  isOpen: boolean;
  onToggle: () => void;
  selectedLineCount: number;
  branchName: string;
}

const MOCK_RESPONSES = [
  "I'll analyze those changes. The code looks well-structured with clean separation of concerns.",
  "Looking at the diff, the implementation follows the established patterns. No issues flagged.",
  "The changes are consistent with the existing codebase style. One minor suggestion: consider adding error boundaries around the new components.",
  "Good approach. The component hierarchy follows atomic design principles correctly.",
];

function AgentPanel({
  isOpen,
  onToggle,
  selectedLineCount,
  branchName,
}: AgentPanelProps) {
  const [messages, setMessages] = useState<AgentMessage[]>([
    { role: "system", content: `Watching branch ${branchName} — reviewing changes` },
    {
      role: "assistant",
      content:
        "This branch looks clean. I'm ready to help review the changes. Select some lines or ask me about the code.",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const responseIndexRef = useRef(0);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = useCallback(() => {
    const text = inputValue.trim();
    if (!text) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInputValue("");

    // Mock assistant response after 500ms
    setTimeout(() => {
      const response =
        MOCK_RESPONSES[responseIndexRef.current % MOCK_RESPONSES.length] ?? "";
      responseIndexRef.current += 1;
      setMessages((prev) => [...prev, { role: "assistant" as const, content: response }]);
    }, 500);
  }, [inputValue]);

  const handleQuickAction = useCallback(
    (action: string) => {
      setMessages((prev) => [...prev, { role: "user", content: action }]);

      setTimeout(() => {
        const response =
          MOCK_RESPONSES[responseIndexRef.current % MOCK_RESPONSES.length] ?? "";
        responseIndexRef.current += 1;
        setMessages((prev) => [...prev, { role: "assistant" as const, content: response }]);
      }, 500);
    },
    []
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

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

      {/* Messages area */}
      <div className="flex-1 overflow-auto p-3 space-y-3">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick actions */}
      <div className="px-3 pb-2 flex flex-wrap gap-1.5">
        {["Explain this change", "Suggest improvements", "Check for bugs"].map(
          (action) => (
            <button
              key={action}
              onClick={() => handleQuickAction(action)}
              className={cn(
                "px-2.5 py-1 text-xs rounded-full",
                "border border-[var(--border)] text-[var(--fg-muted)]",
                "hover:bg-[var(--bg-surface-hover)] hover:text-[var(--fg-default)]",
                "transition-colors"
              )}
            >
              {action}
            </button>
          )
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-[var(--border)] p-3">
        <div className="flex gap-2">
          <textarea
            rows={2}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about this code..."
            className={cn(
              "flex-1 resize-none rounded-md px-3 py-2 text-sm",
              "bg-[var(--bg-inset)] text-[var(--fg-default)]",
              "border border-[var(--border)] placeholder:text-[var(--fg-subtle)]",
              "focus:outline-none focus:border-[var(--accent)]"
            )}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim()}
            className={cn(
              "self-end p-2 rounded-md transition-colors",
              "text-[var(--fg-muted)] hover:text-[var(--fg-default)]",
              "hover:bg-[var(--bg-surface-hover)]",
              "disabled:opacity-40 disabled:cursor-not-allowed"
            )}
          >
            <Icon name="send" size="sm" />
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: AgentMessage }) {
  if (message.role === "system") {
    return (
      <div className="text-center">
        <span className="text-xs italic text-[var(--fg-subtle)]">
          {message.content}
        </span>
      </div>
    );
  }

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-lg px-3 py-2 bg-[var(--bg-canvas)] text-sm text-[var(--fg-default)]">
          {message.content}
        </div>
      </div>
    );
  }

  // assistant
  return (
    <div className="max-w-[85%]">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon name="sparkle" size="xs" className="text-[var(--accent-emerald)]" />
        <span className="text-xs font-medium text-[var(--fg-muted)]">Agent</span>
      </div>
      <div className="rounded-lg px-3 py-2 bg-[var(--bg-surface-hover)] text-sm text-[var(--fg-default)]">
        {message.content}
      </div>
    </div>
  );
}

AgentPanel.displayName = "AgentPanel";

export { AgentPanel };
export type { AgentPanelProps, AgentMessage };
