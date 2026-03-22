import { useState } from "react";
import { AppShell } from "@/components/templates";
import { useStackDetail } from "@/hooks/useStackDetail";
import type { StackConnectorItem } from "@/components/molecules";
import type { TabItem } from "@/components/molecules/TabBar";

function branchTitle(name: string): string {
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
  const [activeIndex, setActiveIndex] = useState(2);
  const [activeTab, setActiveTab] = useState("files");

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

  const activeBranch = data.branches[activeIndex] ?? null;

  const activeStats = mockDiffStats[activeBranch?.branch.id ?? ""];
  const fileCount = activeStats && (activeStats.additions > 0 || activeStats.deletions > 0)
    ? Math.ceil((activeStats.additions + activeStats.deletions) / 20)
    : 0;

  const tabs: TabItem[] = [
    { id: "files", label: "Files changed", count: fileCount || undefined },
  ];

  return (
    <AppShell
      stackName={data.stack.name}
      trunk={data.stack.trunk}
      items={items}
      activeIndex={activeIndex}
      onSelect={setActiveIndex}
      activeBranch={activeBranch}
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
    >
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-3">
          <p className="text-[var(--fg-muted)] text-sm">
            Diff review panel will render here (SB-039).
          </p>
          <p className="font-[family-name:var(--font-mono)] text-xs text-[var(--fg-subtle)]">
            v0.0.1 &middot; Stack Bench
          </p>
        </div>
      </div>
    </AppShell>
  );
}
