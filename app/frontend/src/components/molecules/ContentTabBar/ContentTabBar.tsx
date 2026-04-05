import type { Ref } from "react";
import { Tab, CountBadge, Icon } from "@/components/atoms";
import { UrlInput } from "@/components/atoms/UrlInput";
import type { ContentTab } from "@/types/content";

interface ContentTabBarProps {
  activeTab: ContentTab;
  onTabChange: (tab: ContentTab) => void;
  diffFileCount?: number;
  browserUrl?: string;
  onBrowserUrlChange?: (url: string) => void;
  onBrowserUrlSubmit?: () => void;
  urlInputRef?: Ref<HTMLInputElement>;
}

function ContentTabBar({
  activeTab,
  onTabChange,
  diffFileCount,
  browserUrl,
  onBrowserUrlChange,
  onBrowserUrlSubmit,
  urlInputRef,
}: ContentTabBarProps) {
  return (
    <div
      className="flex items-center gap-0 px-4 border-b border-[var(--border)] bg-[var(--bg-surface)]"
      role="tablist"
      aria-label="Content tabs"
    >
      <Tab
        active={activeTab === "diffs"}
        onClick={() => onTabChange("diffs")}
        aria-label="Stack Diffs tab"
      >
        <Icon name="git-commit" size="xs" />
        Stack Diffs
        {diffFileCount !== undefined && diffFileCount > 0 && (
          <CountBadge count={diffFileCount} />
        )}
      </Tab>
      <Tab
        active={activeTab === "code"}
        onClick={() => onTabChange("code")}
        aria-label="Code tab"
      >
        <Icon name="code" size="xs" />
        Code
      </Tab>
      <Tab
        active={activeTab === "browser"}
        onClick={() => onTabChange("browser")}
        aria-label="Browser tab"
      >
        <Icon name="globe" size="xs" />
        Browser
      </Tab>
      {activeTab === "browser" && onBrowserUrlChange && onBrowserUrlSubmit && (
        <div className="flex-1 min-w-0 ml-3">
          <UrlInput
            ref={urlInputRef}
            value={browserUrl ?? ""}
            onChange={onBrowserUrlChange}
            onSubmit={onBrowserUrlSubmit}
          />
        </div>
      )}
    </div>
  );
}

ContentTabBar.displayName = "ContentTabBar";

export { ContentTabBar };
export type { ContentTabBarProps };
