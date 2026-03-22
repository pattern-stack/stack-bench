import { Tab, CountBadge } from "@/components/atoms";

interface TabItem {
  id: string;
  label: string;
  count?: number;
}

interface TabBarProps {
  tabs: TabItem[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

function TabBar({ tabs, activeTab, onTabChange }: TabBarProps) {
  return (
    <div
      className="flex items-end gap-0 px-6 bg-[var(--bg-surface)] border-b border-[var(--border)]"
      role="tablist"
    >
      {tabs.map((tab) => (
        <Tab
          key={tab.id}
          active={tab.id === activeTab}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.label}
          {tab.count !== undefined && (
            <CountBadge count={tab.count} />
          )}
        </Tab>
      ))}
    </div>
  );
}

TabBar.displayName = "TabBar";

export { TabBar };
export type { TabBarProps, TabItem };
