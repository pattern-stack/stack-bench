import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueries } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import { AppShell } from "@/components/templates";
import { FilesChangedPanel } from "@/components/organisms/FilesChangedPanel";
import { BrowserPanel } from "@/components/organisms/BrowserPanel";
import { FileContent } from "@/components/molecules/FileContent";
import { PathBar } from "@/components/molecules/PathBar";
import { LoginPage } from "@/components/organisms/LoginPage";
import { useAuth } from "@/hooks/useAuth";
import { useStackDetail } from "@/hooks/useStackDetail";
import { useStackList } from "@/hooks/useStackList";
import { useBranchDiff, branchDiffKeys } from "@/hooks/useBranchDiff";
import { useFileTree } from "@/hooks/useFileTree";
import { useFileContent } from "@/hooks/useFileContent";
import { mockActivityEntries } from "@/lib/mock-activity-data";
import type { StackConnectorItem } from "@/components/molecules";
import type { DiffFileListItem } from "@/components/molecules/DiffFileList";
import type { ChangedFileInfo } from "@/components/organisms/FileTree";
import type { DiffData } from "@/types/diff";
import type { SidebarMode } from "@/types/sidebar";
import type { ContentTab } from "@/types/content";
import type { CIStatus, StackSummary, ActivityLogEntry } from "@/types/activity";
import { DiffSkeleton } from "@/components/organisms/FilesChangedPanel/DiffSkeleton";
import { ContentEmptyState } from "@/components/organisms/ContentEmptyState";

import { shortBranch } from "@/lib/short-branch";

interface OnboardingStatus {
  needs_onboarding: boolean;
  has_github: boolean;
  has_project: boolean;
}


/** Status values that count as "draft" (no PR or local-only) */
const DRAFT_STATUSES = new Set(["draft", "created", "local"]);
/** Status values that count as "open" (has a PR, under review) */
const OPEN_STATUSES = new Set(["open", "reviewing", "review", "approved", "ready"]);

function computeSummary(items: StackConnectorItem[]): StackSummary {
  let merged = 0;
  let open = 0;
  let draft = 0;
  let needsRestack = 0;

  for (const item of items) {
    if (item.status === "merged") merged++;
    else if (OPEN_STATUSES.has(item.status)) open++;
    else if (DRAFT_STATUSES.has(item.status)) draft++;
    if (item.needsRestack) needsRestack++;
  }

  return { branchCount: items.length, merged, open, draft, needsRestack };
}

export function App() {
  const { isAuthenticated, isLoading: authLoading, login, register, logout: _logout } = useAuth();
  const navigate = useNavigate();

  // After auth loads, check onboarding status
  const { data: onboardingStatus } = useQuery<OnboardingStatus>({
    queryKey: ["onboarding", "status"],
    queryFn: () => apiClient.get<OnboardingStatus>("/api/v1/onboarding/status"),
    enabled: isAuthenticated,
    staleTime: 30_000,
  });

  // Redirect to onboarding if needed
  useEffect(() => {
    if (onboardingStatus?.needs_onboarding) {
      navigate("/onboarding", { replace: true });
    }
  }, [onboardingStatus, navigate]);

  // Auth gate: show login page if not authenticated
  if (!isAuthenticated && !authLoading) {
    return (
      <LoginPage
        onLogin={async (email, password) => {
          await login(email, password);
        }}
        onRegister={async (firstName, lastName, email, password) => {
          await register(firstName, lastName, email, password);
        }}
      />
    );
  }

  // Show loading while checking auth or onboarding
  if (authLoading || (isAuthenticated && !onboardingStatus)) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] flex items-center justify-center">
        <p className="text-[var(--fg-muted)] text-sm">Loading...</p>
      </div>
    );
  }

  return <AuthenticatedApp />;
}

function AuthenticatedApp() {
  const [selectedStackId, setSelectedStackId] = useState<string | undefined>(undefined);
  const { data, loading, error } = useStackDetail(selectedStackId);
  const [activeIndex, setActiveIndex] = useState(0);
  const [sidebarMode, setSidebarMode] = useState<SidebarMode>("diffs");
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [activityEntries, setActivityEntries] = useState<ActivityLogEntry[]>(mockActivityEntries);
  const [forceExpanded, setForceExpanded] = useState<boolean | null>(null);
  const [floatingComments, setFloatingComments] = useState(true);
  const [contentTab, setContentTab] = useState<ContentTab>("diffs");
  const [browserUrl, setBrowserUrl] = useState("http://localhost:3000");
  const [submittedBrowserUrl, setSubmittedBrowserUrl] = useState("");
  const [hasActivatedBrowser, setHasActivatedBrowser] = useState(false);
  const urlInputRef = useRef<HTMLInputElement>(null);

  // TODO: Lift selectedLineCount from FilesChangedPanel in a future PR
  const selectedLineCount = 0;

  const stackId = data?.stack.id;
  const activeBranchId = data?.branches[activeIndex]?.branch.id;
  const { data: diffData, loading: diffLoading } = useBranchDiff(stackId, activeBranchId);
  const { data: fileTree, loading: treeLoading } = useFileTree(stackId, activeBranchId);
  const { data: fileContent, loading: contentLoading } = useFileContent(stackId, activeBranchId, contentTab === "code" ? selectedPath : null);

  // Fetch all stacks for the same project (for the stack switcher)
  const projectId = data?.stack.project_id;
  const { data: stacks } = useStackList(projectId);

  const handleStackChange = (id: string) => {
    setSelectedStackId(id);
    setActiveIndex(0);
    setSidebarMode("diffs");
    setContentTab("diffs");
    setSelectedPath(null);
    setForceExpanded(null);
  };

  // Track first browser activation to mount iframe lazily
  useEffect(() => {
    if (contentTab === "browser" && !hasActivatedBrowser) {
      setHasActivatedBrowser(true);
    }
  }, [contentTab, hasActivatedBrowser]);

  const handleBrowserUrlSubmit = useCallback(() => {
    setSubmittedBrowserUrl(browserUrl);
  }, [browserUrl]);

  // Subscribe reactively to all branch diffs
  const branchDiffQueries = useQueries({
    queries: (data?.branches ?? []).map((b) => ({
      queryKey: branchDiffKeys.diff(stackId ?? "", b.branch.id),
      queryFn: () => apiClient.get<DiffData>(`/api/v1/stacks/${stackId}/branches/${b.branch.id}/diff`),
      enabled: !!stackId,
      staleTime: Infinity,
    })),
  });

  // Reset sidebar mode, content tab, and selection when branch changes
  useEffect(() => {
    setSidebarMode("diffs");
    setContentTab("diffs");
    setSelectedPath(null);
    setForceExpanded(null);
  }, [activeIndex]);

  // Keyboard shortcuts for content tab switching
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.shiftKey && e.key === "!") {
        e.preventDefault();
        setContentTab("diffs");
      }
      if (mod && e.shiftKey && e.key === "@") {
        e.preventDefault();
        setContentTab("code");
      }
      if (mod && e.shiftKey && e.key === "#") {
        e.preventDefault();
        setContentTab("browser");
      }
      if (mod && e.key === "l" && contentTab === "browser") {
        e.preventDefault();
        urlInputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [contentTab]);

  // Build changed files map for dirty state in file explorer
  const changedFiles = useMemo(() => {
    if (!diffData) return undefined;
    const map = new Map<string, ChangedFileInfo>();
    for (const f of diffData.files) {
      map.set(f.path, {
        changeType: f.change_type,
        additions: f.additions,
        deletions: f.deletions,
      });
    }
    return map;
  }, [diffData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] flex items-center justify-center">
        <p className="text-[var(--fg-muted)] text-sm">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] flex items-center justify-center">
        <p className="text-[var(--red)] text-sm">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <AppShell
        agentOpen={agentOpen}
        onAgentToggle={() => setAgentOpen((prev) => !prev)}
      >
        <ContentEmptyState />
      </AppShell>
    );
  }

  const items: StackConnectorItem[] = data.branches.map((b, index) => {
    const displayStatus = b.pull_request?.state ?? b.branch.state;
    const diffResult = branchDiffQueries[index]?.data;

    return {
      id: b.branch.id,
      title: shortBranch(b.branch.name),
      status: displayStatus,
      additions: diffResult?.total_additions,
      deletions: diffResult?.total_deletions,
      prNumber: b.pull_request?.external_id ?? null,
      ciStatus: "none" as CIStatus,
      needsRestack: b.needs_restack ?? false,
    };
  });

  const summary = computeSummary(items);
  const activeBranch = data.branches[activeIndex] ?? null;

  // Derive DiffFileListItem[] from diff data
  const diffFiles: DiffFileListItem[] = (diffData?.files ?? []).map((f) => {
    const fileName = f.path.includes("/")
      ? f.path.slice(f.path.lastIndexOf("/") + 1)
      : f.path;
    return {
      path: f.path,
      fileName,
      changeType: f.change_type,
      additions: f.additions,
      deletions: f.deletions,
    };
  });

  const fileCount = diffData?.files.length ?? 0;

  return (
    <AppShell
      stackName={data.stack.name}
      trunk={data.stack.trunk}
      stacks={stacks}
      onStackChange={handleStackChange}
      items={items}
      activeIndex={activeIndex}
      onSelect={setActiveIndex}
      activeBranch={activeBranch}
      agentOpen={agentOpen}
      onAgentToggle={() => setAgentOpen((prev) => !prev)}
      selectedLineCount={selectedLineCount}
      sidebarMode={sidebarMode}
      onSidebarModeChange={setSidebarMode}
      diffFiles={diffFiles}
      fileTree={fileTree}
      selectedPath={selectedPath}
      onSelectFile={setSelectedPath}
      diffFileCount={fileCount}
      changedFiles={changedFiles}
      summary={summary}
      activityEntries={activityEntries}
      onSync={() => console.log("sync trunk")}
      onMerge={() => setMergeOpen(true)}
      mergeOpen={mergeOpen}
      onMergeClose={() => setMergeOpen(false)}
      stackId={stackId}
      branches={data.branches}
      onClearActivity={() => setActivityEntries([])}
      fileCount={diffData?.files.length}
      additions={diffData?.total_additions}
      deletions={diffData?.total_deletions}
      onCollapseAll={() => setForceExpanded(false)}
      onExpandAll={() => setForceExpanded(true)}
      floatingComments={floatingComments}
      onToggleCommentMode={() => setFloatingComments((prev) => !prev)}
      diffLoading={diffLoading}
      treeLoading={treeLoading}
      contentTab={contentTab}
      onContentTabChange={setContentTab}
      browserUrl={browserUrl}
      onBrowserUrlChange={setBrowserUrl}
      onBrowserUrlSubmit={handleBrowserUrlSubmit}
      urlInputRef={urlInputRef}
    >
      {contentTab === "diffs" && (
        diffLoading ? (
          <DiffSkeleton />
        ) : diffData ? (
          <FilesChangedPanel
            diffData={diffData}
            forceExpanded={forceExpanded}
            stackId={stackId}
            branchId={activeBranchId}
            pullRequestId={activeBranch?.pull_request?.id}
            floatingComments={floatingComments}
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-[var(--fg-muted)] text-sm">Select a branch to view changes</p>
          </div>
        )
      )}
      {contentTab === "code" && (
        contentLoading ? (
          <DiffSkeleton />
        ) : fileContent ? (
          <>
            <PathBar path={fileContent.path} />
            <div className="flex-1 min-h-0 overflow-hidden">
              <FileContent file={fileContent} />
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-[var(--fg-muted)] text-sm">
              {selectedPath ? "File not available" : "Select a file to view its contents"}
            </p>
          </div>
        )
      )}
      {/* BrowserPanel: mount on first activation, then persist with display:none */}
      {hasActivatedBrowser && (
        <div style={{ display: contentTab === "browser" ? "contents" : "none" }}>
          <BrowserPanel url={submittedBrowserUrl} />
        </div>
      )}
    </AppShell>
  );
}
