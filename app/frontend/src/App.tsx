import { useState } from "react";
import { StackSidebar } from "@/components/organisms";
import { useStackDetail } from "@/hooks/useStackDetail";
import type { StackConnectorItem } from "@/components/molecules";

function branchTitle(name: string): string {
  // Extract the last segment: "dug/frontend-mvp/3-stack-nav" → "3-stack-nav"
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}

const mockDiffStats: Record<string, { additions: number; deletions: number }> = {
  "b-001": { additions: 48, deletions: 12 },
  "b-002": { additions: 156, deletions: 23 },
  "b-003": { additions: 89, deletions: 34 },
  "b-004": { additions: 0, deletions: 0 },
};

export function App() {
  const { data, loading, error } = useStackDetail();
  const [activeIndex, setActiveIndex] = useState(2); // Default to 3rd branch (current work)

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] flex items-center justify-center">
        <p className="text-[var(--fg-muted)] text-sm">Loading...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] flex items-center justify-center">
        <p className="text-[var(--red)] text-sm">{error ?? "No data"}</p>
      </div>
    );
  }

  const items: StackConnectorItem[] = data.branches.map((b) => {
    // Determine the display status: prefer PR state over branch state
    const displayStatus = b.pull_request?.state ?? b.branch.state;
    const stats = mockDiffStats[b.branch.id] ?? { additions: 0, deletions: 0 };

    return {
      id: b.branch.id,
      title: branchTitle(b.branch.name),
      status: displayStatus,
      additions: stats.additions,
      deletions: stats.deletions,
    };
  });

  return (
    <div className="flex h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] font-[family-name:var(--font-sans)]">
      <StackSidebar
        stackName={data.stack.name}
        trunk={data.stack.trunk}
        items={items}
        activeIndex={activeIndex}
        onSelect={setActiveIndex}
      />
      {/* Main content area — placeholder until SB-038 (App Shell) */}
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-semibold tracking-tight">
            {items[activeIndex]?.title ?? "Select a branch"}
          </h1>
          <p className="text-[var(--fg-muted)] text-sm">
            Diff review panel will render here (SB-039).
          </p>
          <p className="font-[family-name:var(--font-mono)] text-xs text-[var(--fg-subtle)]">
            v0.0.1 &middot; Stack Bench
          </p>
        </div>
      </main>
    </div>
  );
}
