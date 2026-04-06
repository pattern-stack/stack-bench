import { useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import { useTaskDetail } from "@/hooks/useTaskDetail";
import { useConversationForEntity } from "@/hooks/useConversationForEntity";
import { apiClient } from "@/generated/api/client";
import { Icon } from "@/components/atoms";
import { ChatRoom } from "@/components/organisms/ChatRoom/ChatRoom";
import { ChatMessageRow } from "@/components/molecules/ChatMessageRow";
import { demoPhases, type DemoPhase } from "@/lib/demo-chat-data";
import type { AgentPhase } from "@/types/task";

function WorkspaceDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const { data, loading, error } = useTaskDetail(taskId);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const { conversation } = useConversationForEntity("task", taskId, "execution");

  const handleSendMessage = useCallback(
    (text: string) => {
      if (!conversation) return;
      apiClient.post(`/api/v1/conversations/${conversation.id}/send`, {
        message: text,
      });
    },
    [conversation],
  );

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-[var(--fg-muted)]">Loading workspace...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-[var(--red)]">
          {error ?? "Task not found"}
        </p>
      </div>
    );
  }

  const { task, job, agent_runs } = data;

  // Use real agent_runs if available, otherwise show demo for active tasks
  const isActive =
    task.state === "in_progress" || task.state === "in_review";
  const showDemo = agent_runs.length === 0 && isActive;

  // Build pipeline from demo phases or real agent runs
  const pipelinePhases: { role: string; state: "completed" | "active" | "pending" }[] =
    showDemo
      ? demoPhases.map((p, i) => ({
          role: p.role,
          state:
            i < demoPhases.length - 1
              ? "completed"
              : ("active" as const),
        }))
      : agent_runs.map((r) => ({
          role: r.phase,
          state:
            r.state === "complete"
              ? ("completed" as const)
              : r.state === "running"
                ? ("active" as const)
                : ("pending" as const),
        }));

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Task header */}
      <div className="px-4 py-3 border-b border-[var(--border-muted)] flex items-center gap-3">
        <span className="text-xs font-mono text-[var(--fg-muted)]">
          {task.reference_number ?? task.id.slice(0, 8)}
        </span>
        <h1 className="text-sm font-semibold text-[var(--fg-default)] truncate">
          {task.title}
        </h1>
        <StatusBadge state={task.state} />
        {job && (
          <span className="text-xs text-[var(--fg-subtle)] ml-auto">
            {job.current_phase ?? job.state}
          </span>
        )}
      </div>

      {/* Pipeline bar */}
      {pipelinePhases.length > 0 && (
        <PipelineBar phases={pipelinePhases} />
      )}

      {/* Main content area */}
      <div className="flex-1 flex min-h-0">
        {/* Chat area */}
        <div className="flex-[3] flex flex-col min-w-0 border-r border-[var(--border-muted)]">
          {conversation ? (
            <ChatRoom
              channel={`conversation:${conversation.id}`}
              agentName={conversation.agent_name}
              onSendMessage={handleSendMessage}
            />
          ) : (
            <>
              <div className="flex-1 overflow-y-auto">
                {showDemo ? (
                  <DemoChatStream phases={demoPhases} />
                ) : agent_runs.length === 0 ? (
                  <div className="flex-1 flex items-center justify-center h-full">
                    <div className="text-center py-20">
                      <Icon
                        name="message-square"
                        size="lg"
                        className="text-[var(--fg-subtle)] mx-auto mb-2"
                      />
                      <p className="text-sm text-[var(--fg-muted)]">
                        No agent activity yet
                      </p>
                      <p className="text-xs text-[var(--fg-subtle)] mt-1">
                        Start a job to see agent chat here
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 space-y-4">
                    {agent_runs.map((phase) => (
                      <PhaseSection key={phase.id} phase={phase} />
                    ))}
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Chat input (demo/fallback mode) */}
              <div className="px-4 py-3 border-t border-[var(--border-muted)]">
                <div className="flex items-center gap-2 bg-[var(--bg-surface)] rounded-lg border border-[var(--border-muted)] px-3 py-2">
                  <input
                    type="text"
                    placeholder="Ask the agent..."
                    className="flex-1 bg-transparent text-sm text-[var(--fg-default)] placeholder:text-[var(--fg-subtle)] outline-none"
                  />
                  <button className="text-[var(--accent)] hover:text-[var(--fg-default)] transition-colors">
                    <Icon name="send" size="sm" />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Changes panel */}
        <div className="flex-[2] flex flex-col min-w-0">
          <div className="px-4 py-2 border-b border-[var(--border-muted)]">
            <div className="flex items-center gap-4">
              <span className="text-xs font-semibold text-[var(--fg-default)]">
                Changes
              </span>
              <span className="text-xs text-[var(--fg-subtle)]">History</span>
              <span className="text-xs text-[var(--fg-subtle)]">
                Discussion
              </span>
            </div>
          </div>

          {/* File list from demo data */}
          {showDemo ? (
            <div className="flex-1 overflow-y-auto">
              <div className="px-4 py-2 text-[10px] text-[var(--fg-subtle)] border-b border-[var(--border-muted)]">
                4 files changed
              </div>
              {[
                { path: "src/auth/oauth_config.ts", change: "M", adds: 2, dels: 1 },
                { path: "src/auth/pkce.ts", change: "A", adds: 18, dels: 0 },
                { path: "src/auth/token_exchange.ts", change: "M", adds: 8, dels: 2 },
                { path: "src/auth/legacy_flow.ts", change: "D", adds: 0, dels: 24 },
              ].map((f) => (
                <div
                  key={f.path}
                  className="flex items-center gap-2 px-4 py-1.5 hover:bg-[var(--bg-canvas-inset)] cursor-pointer text-xs"
                >
                  <span
                    className={`w-4 text-center font-mono text-[10px] font-bold ${
                      f.change === "A"
                        ? "text-[var(--green)]"
                        : f.change === "D"
                          ? "text-[var(--red)]"
                          : "text-[var(--yellow)]"
                    }`}
                  >
                    {f.change}
                  </span>
                  <span className="text-[var(--fg-muted)] font-mono truncate">
                    {f.path}
                  </span>
                  <span className="ml-auto text-[10px] font-mono shrink-0">
                    <span className="text-[var(--green)]">+{f.adds}</span>{" "}
                    <span className="text-[var(--red)]">-{f.dels}</span>
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-xs text-[var(--fg-subtle)]">No changes yet</p>
            </div>
          )}

          {/* Bottom action bar */}
          <div className="px-4 py-3 border-t border-[var(--border-muted)] flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-[var(--fg-muted)]">
              <Icon name="git-branch" size="xs" />
              <span className="font-mono">
                {job?.repo_branch ?? (task?.title ? `task/${task.title.toLowerCase().replace(/\s+/g, '-').slice(0, 40)}` : "—")}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button className="px-3 py-1.5 text-xs text-[var(--fg-muted)] border border-[var(--border-muted)] rounded-md hover:border-[var(--border)] transition-colors">
                Add to Stack
              </button>
              <button className="px-3 py-1.5 text-xs text-[var(--fg-on-accent)] bg-[var(--accent)] rounded-md hover:opacity-90 transition-opacity">
                Create PR
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Render the demo chat stream with phase dividers and real Chat components */
function DemoChatStream({ phases }: { phases: DemoPhase[] }) {
  return (
    <div className="p-4 space-y-2">
      {phases.map((phase) => (
        <div key={phase.role}>
          {/* Phase divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-[var(--border-muted)]" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)]">
              Phase: {phase.role}
            </span>
            <div className="flex-1 h-px bg-[var(--border-muted)]" />
          </div>

          {/* Messages using real ChatMessageRow */}
          <div className="space-y-4">
            {phase.messages.map((msg) => (
              <ChatMessageRow
                key={msg.id}
                message={msg}
                agentName={
                  msg.role === "assistant" ? phase.role : undefined
                }
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/** Compact pipeline bar */
function PipelineBar({
  phases,
}: {
  phases: { role: string; state: "completed" | "active" | "pending" }[];
}) {
  return (
    <div className="px-4 py-2 border-b border-[var(--border-muted)] bg-[var(--bg-surface)]">
      <div className="flex items-center gap-1">
        {phases.map((phase, i) => (
          <div key={i} className="flex items-center gap-1">
            {i > 0 && <div className="w-4 h-px bg-[var(--border-muted)]" />}
            <PhaseNode phase={phase} />
          </div>
        ))}
      </div>
    </div>
  );
}

const ROLE_COLORS: Record<string, string> = {
  Architect: "var(--accent)",
  architect: "var(--accent)",
  Builder: "var(--green)",
  builder: "var(--green)",
  Validator: "var(--purple)",
  validator: "var(--purple)",
};

function PhaseNode({
  phase,
}: {
  phase: { role: string; state: "completed" | "active" | "pending" };
}) {
  const color = ROLE_COLORS[phase.role] ?? "var(--fg-muted)";

  return (
    <button className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-[var(--bg-canvas-inset)] transition-colors">
      {phase.state === "completed" ? (
        <Icon name="check" size="xs" className="text-[var(--fg-subtle)]" />
      ) : phase.state === "active" ? (
        <span
          className="w-2 h-2 rounded-full animate-pulse"
          style={{ backgroundColor: color }}
        />
      ) : (
        <span className="w-2 h-2 rounded-full border border-[var(--border-muted)]" />
      )}
      <span
        className={`text-xs capitalize ${
          phase.state === "active"
            ? "text-[var(--fg-default)] font-medium"
            : "text-[var(--fg-muted)]"
        }`}
      >
        {phase.role}
      </span>
    </button>
  );
}

function PhaseSection({ phase }: { phase: AgentPhase }) {
  const color = ROLE_COLORS[phase.phase] ?? "var(--fg-muted)";

  return (
    <div>
      <div className="flex items-center gap-3 my-4">
        <div className="flex-1 h-px bg-[var(--border-muted)]" />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)]">
          Phase: {phase.phase}
        </span>
        <div className="flex-1 h-px bg-[var(--border-muted)]" />
      </div>
      <div className="flex items-start gap-3">
        <span
          className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-[var(--bg-canvas)] shrink-0"
          style={{ backgroundColor: color }}
        >
          {phase.phase.charAt(0).toUpperCase()}
        </span>
        <div className="text-sm text-[var(--fg-muted)]">
          {phase.state === "running"
            ? `${phase.phase} is working...`
            : phase.state === "complete"
              ? `${phase.phase} completed`
              : `${phase.phase} pending`}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ state }: { state: string }) {
  const colors: Record<string, string> = {
    backlog: "var(--fg-subtle)",
    ready: "var(--yellow)",
    in_progress: "var(--accent)",
    in_review: "var(--purple)",
    done: "var(--green)",
    cancelled: "var(--red)",
  };
  const color = colors[state] ?? "var(--fg-subtle)";

  return (
    <span
      className="px-1.5 py-0.5 rounded text-[10px] font-medium capitalize"
      style={{ color, border: `1px solid ${color}40` }}
    >
      {state.replace("_", " ")}
    </span>
  );
}

WorkspaceDetailPage.displayName = "WorkspaceDetailPage";

export { WorkspaceDetailPage };
