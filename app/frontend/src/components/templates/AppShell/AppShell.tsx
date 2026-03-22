import type { ReactNode } from "react";
import { StackSidebar } from "@/components/organisms/StackSidebar";
import { PRHeader } from "@/components/molecules/PRHeader";
import { TabBar } from "@/components/molecules/TabBar";
import type { TabItem } from "@/components/molecules/TabBar";
import { ActionBar } from "@/components/molecules/ActionBar";
import type { StackConnectorItem } from "@/components/molecules/StackConnector";
import type { BranchWithPR } from "@/types/stack";

interface AppShellProps {
  stackName: string;
  trunk: string;
  items: StackConnectorItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
  activeBranch: BranchWithPR | null;
  tabs: TabItem[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  children?: ReactNode;
}

/** Extract short branch name from full ref: "dug/frontend-mvp/3-stack-nav" → "3-stack-nav" */
function shortBranch(name: string): string {
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}

function AppShell({
  stackName,
  trunk,
  items,
  activeIndex,
  onSelect,
  activeBranch,
  tabs,
  activeTab,
  onTabChange,
  children,
}: AppShellProps) {
  // Derive PRHeader props from the active branch
  const pr = activeBranch?.pull_request;
  const branchName = activeBranch?.branch.name ?? "";
  const title = pr?.title ?? shortBranch(branchName);
  const description = pr?.description ?? (pr ? null : "No pull request");
  const headBranch = shortBranch(branchName);

  // Base branch: for position 1, base is trunk. For others, it's the previous branch.
  const position = activeBranch?.branch.position ?? 1;
  const baseBranch = position <= 1 ? trunk : shortBranch(
    // Find branch at position - 1
    items[activeIndex - 1]?.title ?? trunk
  );

  // Display status: prefer PR state over branch state
  const displayStatus = pr?.state ?? activeBranch?.branch.state ?? "created";

  return (
    <div className="flex h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] font-[family-name:var(--font-sans)]">
      <StackSidebar
        stackName={stackName}
        trunk={trunk}
        items={items}
        activeIndex={activeIndex}
        onSelect={onSelect}
      />
      <main className="flex-1 flex flex-col min-w-0">
        <PRHeader
          title={title}
          baseBranch={baseBranch}
          headBranch={headBranch}
          description={description}
        />
        <TabBar
          tabs={tabs}
          activeTab={activeTab}
          onTabChange={onTabChange}
        />
        <div className="flex-1 overflow-auto">
          {children}
        </div>
        <ActionBar status={displayStatus} />
      </main>
    </div>
  );
}

AppShell.displayName = "AppShell";

export { AppShell };
export type { AppShellProps };
