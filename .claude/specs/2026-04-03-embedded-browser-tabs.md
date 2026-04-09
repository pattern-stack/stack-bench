---
title: Embedded Browser Panel & Tabbed Content Area
status: draft
created: 2026-04-03
branch:
stack:
stack_index:
depends_on:
---

# Embedded Browser Panel & Tabbed Content Area

## Problem

The Stack Bench main content area currently switches between two views controlled by the sidebar mode toggle (`SidebarMode: "diffs" | "files"`). The toggle lives in the sidebar and swaps both the sidebar tree view and the main content in lockstep. There is no way to view a web page alongside diffs or code, and no concept of independent content tabs.

For a developer workbench, being able to preview a deployed PR, check a staging environment, or view documentation without leaving the app is essential. The current architecture has no extension point for adding new content panel types beyond diffs and file viewing.

## Solution

Add a tabbed content area to the main panel (between PRHeader and the content viewport) and introduce a new "Browser" tab that renders an iframe-based web viewer. The three tabs are:

1. **Stack Diffs** -- the existing `FilesChangedPanel` diff review (current default)
2. **Code** -- the existing `FileContent` file viewer (currently triggered by sidebar "Files" mode)
3. **Browser** -- a new embedded iframe panel for rendering web pages

### Key Design Decisions

**Tabs control the main content area independently from the sidebar.** The sidebar mode toggle (`Diffs | Files`) controls which tree view appears in the sidebar. The content tabs control what renders in the main viewport. This decouples sidebar navigation from content display -- you can browse the file tree in the sidebar while viewing a diff, or view the diff file list while previewing a URL in the browser.

**Iframe-based browser for web-first.** The simplest approach that works today in any React web app. No Electron, Tauri, or native dependencies. The iframe loads any URL the host browser can reach, subject to standard same-origin/CORS/X-Frame-Options restrictions. Most internal tools, staging deployments, and localhost servers will work. Sites that set `X-Frame-Options: DENY` or `Content-Security-Policy: frame-ancestors 'none'` will not render. **Note:** the `<iframe>` `onError` event does *not* fire for X-Frame-Options/CSP blocks — the iframe loads blank and `onLoad` still fires. Reliable detection of frame-blocking is not possible in web mode; the BrowserPanel should show a generic "page may not support embedding" hint with an "Open in new tab" link, rather than claiming to detect the error. This limitation goes away in Tauri/WKWebView mode.

**Future path to native macOS.** When Stack Bench becomes a Tauri desktop app, the iframe can be swapped for a Tauri `<webview>` backed by WKWebView, which bypasses iframe restrictions entirely. The component boundary (`BrowserPanel`) is designed as a seam for this swap -- the rest of the app talks to it via props (`url`, `onNavigate`, `onLoad`, `onError`), not iframe-specific APIs.

## Current State

### Layout hierarchy (AppShell.tsx)

```
<div class="flex h-screen">
  <StackSidebar />            <!-- 320px fixed left -->
  <main class="flex-1 flex flex-col">
    <PRHeader />              <!-- fixed header -->
    <div class="flex-1 overflow-auto">
      {children}              <!-- content: FilesChangedPanel or FileContent -->
    </div>
  </main>
  <AgentPanel />              <!-- collapsible right panel -->
</div>
```

### Content switching (App.tsx, lines 267-303)

Content is driven by `sidebarMode` state:
- `sidebarMode === "diffs"` renders `<FilesChangedPanel />`
- `sidebarMode === "files"` renders `<PathBar /> + <FileContent />`

Both sidebar tree and main content change together. There is no tab bar -- the sidebar toggle is the only control.

### Existing Tab atom

The codebase already has a `Tab` atom (`components/atoms/Tab/Tab.tsx`) and a `CountBadge` companion. The `Tab` atom renders a button with `role="tab"`, `aria-selected`, and an underline border for the active state. It is not currently used anywhere in the app (the original TabBar from SB-038 was replaced by the sidebar mode toggle in the sidebar-layout-merge spec).

## Architecture

### New type: `ContentTab`

```ts
// types/content.ts
export type ContentTab = "diffs" | "code" | "browser";
```

This is distinct from `SidebarMode` (which remains `"diffs" | "files"`). The sidebar mode controls sidebar tree display. The content tab controls main viewport content.

### Replace existing `TabBar` molecule with `ContentTabBar`

**Layer:** Molecule (composes Tab atoms with state management)

The codebase already has a `TabBar` molecule at `components/molecules/TabBar/TabBar.tsx` that composes the same `Tab` and `CountBadge` atoms. It is currently unused (the original SB-038 TabBar was replaced by the sidebar mode toggle). Rather than creating a duplicate, **delete the existing `TabBar` directory** and create `ContentTabBar` as its replacement. The new molecule adds trailing content support (URL input) that the old `TabBar` lacked.

A horizontal tab bar that renders inside `<main>`, between `PRHeader` and the content viewport. Uses the existing `Tab` atom and `CountBadge`.

```
┌────────────────────────────────────────────────────────────┐
│ PRHeader                                                    │
├────────────────────────────────────────────────────────────┤
│ [Stack Diffs (12)] [Code] [Browser]              [url bar]  │
├────────��────────────────────────────��──────────────────────┤
│                                                              │
│  Content viewport (scrollable)                              │
│                                                              │
└────────��───────────────────────────────────────────────────┘
```

Props:
```ts
interface ContentTabBarProps {
  activeTab: ContentTab;
  onTabChange: (tab: ContentTab) => void;
  diffFileCount?: number;
  browserUrl?: string;
  onBrowserUrlChange?: (url: string) => void;
  onBrowserUrlSubmit?: () => void;
}
```

The tab bar shows:
- "Stack Diffs" with a `CountBadge` showing the changed file count
- "Code" (plain label)
- "Browser" (plain label)

When the Browser tab is active, a compact URL input field appears inline to the right of the tabs, allowing the user to type or paste a URL and press Enter to navigate.

### New organism: `BrowserPanel`

**Layer:** Organism (interface component, thin wrapper over an iframe)

Renders an iframe that loads the provided URL. Handles loading state, error detection, and URL bar integration.

Props:
```ts
interface BrowserPanelProps {
  url: string;
  onNavigate?: (url: string) => void;
  onLoad?: () => void;
  onError?: (error: string) => void;
}
```

Internal structure:
- An `<iframe>` that fills the content viewport (`width: 100%, height: 100%`)
- A loading spinner overlay while the iframe loads
- Error/unloadable state: show a fallback with the URL and an "Open in new tab" link. Note: iframe `onError` does not fire for X-Frame-Options/CSP blocks, so this is best-effort — show the hint after a timeout or when the user reports the page is blank
- The iframe uses `sandbox="allow-scripts allow-same-origin allow-forms allow-popups"` for reasonable security defaults

### New atom: `UrlInput`

**Layer:** Atom (pure visual input with submit behavior)

A compact, inline URL input field styled to match the design system. Shows a globe/link icon prefix, the URL text, and submits on Enter.

```ts
interface UrlInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  className?: string;
}
```

### New icon additions

The `Icon` atom needs two new icons:
- `globe` -- for the URL input prefix and Browser tab
- `code` -- for the Code tab (currently no code-specific icon exists; `file` is available but `code` with angle brackets is more semantic)

## Component Hierarchy

```
AppShell (template)
  StackSidebar (organism) -- unchanged
  <main>
    PRHeader (molecule) -- unchanged
    ContentTabBar (molecule) -- NEW
      Tab (atom) -- existing, reused
      CountBadge (atom) -- existing, reused
      UrlInput (atom) -- NEW (shown when browser tab active)
    <content viewport>
      FilesChangedPanel (organism) -- existing, shown when tab=diffs
      PathBar + FileContent (molecules) -- existing, shown when tab=code
      BrowserPanel (organism) -- NEW, shown when tab=browser
    </content viewport>
  </main>
  AgentPanel (organism) -- unchanged
```

## Decoupling Sidebar Mode from Content Tab

Today `sidebarMode` drives both sidebar tree and main content. After this change:

| State | Sidebar tree | Main content |
|-------|-------------|--------------|
| `sidebarMode=diffs`, `contentTab=diffs` | Diff file list | FilesChangedPanel |
| `sidebarMode=diffs`, `contentTab=code` | Diff file list | FileContent (last selected file) |
| `sidebarMode=diffs`, `contentTab=browser` | Diff file list | BrowserPanel |
| `sidebarMode=files`, `contentTab=diffs` | Full file tree | FilesChangedPanel |
| `sidebarMode=files`, `contentTab=code` | Full file tree | FileContent |
| `sidebarMode=files`, `contentTab=browser` | Full file tree | BrowserPanel |

The sidebar file selection behavior stays the same: clicking a file in the diff list or file tree sets `selectedPath`. If the user is on the Code tab, the clicked file renders immediately. If they are on the Diffs tab, the diff scrolls to that file. The Browser tab is independent of file selection.

**Backward compatibility:** When `contentTab` is `diffs` and `sidebarMode` is `diffs`, the behavior is identical to today. The default state on page load is `contentTab=diffs`, `sidebarMode=diffs`.

**Smart tab switching:** Clicking a file in the sidebar when the Code tab is not active could optionally switch to the Code tab. This is a UX question addressed in Open Questions.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+Shift+1` / `Ctrl+Shift+1` | Switch to Stack Diffs tab |
| `Cmd+Shift+2` / `Ctrl+Shift+2` | Switch to Code tab |
| `Cmd+Shift+3` / `Ctrl+Shift+3` | Switch to Browser tab |
| `Cmd+L` / `Ctrl+L` | Focus browser URL bar (when on Browser tab) |

**Why `Cmd+Shift+N` instead of `Cmd+N`?** In browser mode, `Cmd+1/2/3` are consumed by the browser chrome (tab switching) before the page's `keydown` listener fires. `Cmd+Shift+1/2/3` avoids this conflict. When Stack Bench runs as a Tauri desktop app, we can reclaim `Cmd+1/2/3` since there are no browser chrome shortcuts to conflict with.

These are implemented via a `useEffect` with `keydown` listener in `AuthenticatedApp`, following the same pattern as other keyboard handlers in the app.

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Types + ContentTabBar molecule | -- |
| 2 | Decouple sidebar mode from content tab in App.tsx and AppShell | Phase 1 |
| 3 | BrowserPanel organism + UrlInput atom | Phase 1 |
| 4 | Keyboard shortcuts + polish | Phase 2, Phase 3 |

## Phase Details

### Phase 1: Types + ContentTabBar molecule

Create the `ContentTab` type and the `ContentTabBar` molecule. Add the `globe` and `code` icons to the Icon atom.

#### File: `app/frontend/src/types/content.ts` (new)

```ts
export type ContentTab = "diffs" | "code" | "browser";
```

#### File: `app/frontend/src/components/atoms/Icon/Icon.tsx` (modify)

Add two new icon path entries to `iconPaths`:

- `globe`: a circle with meridian/equator lines (standard Lucide globe icon)
- `code`: angle brackets `< />` (standard Lucide code icon)

#### File: `app/frontend/src/components/atoms/UrlInput/UrlInput.tsx` (new)

A compact inline input with:
- Globe icon prefix (`Icon name="globe" size="xs"`)
- Text input with `type="url"`, monospace font
- `onKeyDown` handler: Enter triggers `onSubmit`
- Styling: `bg-[var(--bg-inset)]`, `border border-[var(--border)]`, `rounded-md`, `h-7`, `text-xs`, `font-[var(--font-mono)]`
- Takes up remaining horizontal space in the tab bar (flex-1) when visible

#### File: `app/frontend/src/components/atoms/UrlInput/index.ts` (new)

Barrel export.

#### File: `app/frontend/src/components/atoms/index.ts` (modify)

Add `UrlInput` export.

#### File: `app/frontend/src/components/molecules/ContentTabBar/ContentTabBar.tsx` (new)

Renders a `<div role="tablist">` with three `Tab` atoms:
- "Stack Diffs" -- `Icon name="git-commit" size="xs"` + label + `CountBadge` with `diffFileCount`
- "Code" -- `Icon name="code" size="xs"` + label
- "Browser" -- `Icon name="globe" size="xs"` + label

When `activeTab === "browser"`, render `<UrlInput>` after the tabs, filling remaining width.

Styling: `flex items-center gap-0 px-4 border-b border-[var(--border)] bg-[var(--bg-surface)]`. Tab bar height matches PRHeader bottom toolbar row aesthetic.

#### File: `app/frontend/src/components/molecules/ContentTabBar/index.ts` (new)

Barrel export.

#### File: `app/frontend/src/components/molecules/index.ts` (modify)

Add `ContentTabBar` export.

#### Files summary

| File | Action |
|------|--------|
| `src/types/content.ts` | Create |
| `src/components/atoms/Icon/Icon.tsx` | Modify (add 2 icons) |
| `src/components/atoms/UrlInput/UrlInput.tsx` | Create |
| `src/components/atoms/UrlInput/index.ts` | Create |
| `src/components/atoms/index.ts` | Modify (add UrlInput export) |
| `src/components/molecules/TabBar/` | **Delete** (unused, replaced by ContentTabBar) |
| `src/components/molecules/ContentTabBar/ContentTabBar.tsx` | Create |
| `src/components/molecules/ContentTabBar/index.ts` | Create |
| `src/components/molecules/index.ts` | Modify (remove TabBar export, add ContentTabBar) |

---

### Phase 2: Decouple sidebar mode from content tab

Introduce `contentTab` state in `AuthenticatedApp`, wire it through `AppShell`, and render `ContentTabBar` in the main area. The sidebar mode toggle continues to control sidebar trees independently.

#### File: `app/frontend/src/App.tsx` (modify)

Changes to `AuthenticatedApp`:

1. Add state: `const [contentTab, setContentTab] = useState<ContentTab>("diffs");`
2. Add state: `const [browserUrl, setBrowserUrl] = useState("http://localhost:3000");`
3. Pass `contentTab`, `onContentTabChange`, `browserUrl`, `onBrowserUrlChange`, `diffFileCount` to `AppShell`
4. Change the children rendering logic:
   - Current: switches on `sidebarMode`
   - New: switches on `contentTab`
     - `contentTab === "diffs"` -- render `FilesChangedPanel` (same as today)
     - `contentTab === "code"` -- render `PathBar + FileContent` (same as today's `sidebarMode === "files"` content)
     - `contentTab === "browser"` -- render `BrowserPanel`

5. **Fix `useFileContent` hook gating.** Currently (line ~120) the hook is gated on `sidebarMode === "files"`:
   ```ts
   useFileContent(stackId, activeBranchId, sidebarMode === "files" ? selectedPath : null)
   ```
   Change this to gate on `contentTab === "code"`:
   ```ts
   useFileContent(stackId, activeBranchId, contentTab === "code" ? selectedPath : null)
   ```
   Without this change, the Code tab would show "Select a file" even when `selectedPath` is set.

6. **Iframe mount/persist strategy.** Add a `hasActivatedBrowser` boolean state (`useState(false)`, set to `true` when `contentTab` first becomes `"browser"`). Render BrowserPanel using visibility rather than conditional mounting:
   ```tsx
   {/* BrowserPanel: mount on first activation, then persist with display:none */}
   {hasActivatedBrowser && (
     <div style={{ display: contentTab === "browser" ? "contents" : "none" }}>
       <BrowserPanel url={browserUrl} ... />
     </div>
   )}
   ```
   This avoids reloading the iframe every time the user switches tabs. The `hasActivatedBrowser` guard ensures we don't load the iframe until the user first clicks the Browser tab.

7. **PRHeader toolbar visibility.** The PRHeader toolbar (expand/collapse all, comment mode toggle) is diff-specific. Conditionally render the toolbar row only when `contentTab === "diffs"`. Pass `contentTab` to AppShell/PRHeader or use a `showToolbar` boolean prop.

8. The `sidebarMode` state remains and continues to control sidebar tree display. Remove the coupling where `sidebarMode` also controlled main content.

#### File: `app/frontend/src/components/templates/AppShell/AppShell.tsx` (modify)

Changes to `AppShellProps`:
- Add: `contentTab?: ContentTab`
- Add: `onContentTabChange?: (tab: ContentTab) => void`
- Add: `browserUrl?: string`
- Add: `onBrowserUrlChange?: (url: string) => void`
- Add: `onBrowserUrlSubmit?: () => void`
- Add: `diffFileCount?: number` (already passed as `fileCount`, may reuse)

In the render, insert `<ContentTabBar>` between `<PRHeader>` and the content viewport `<div>`:

```tsx
<main className="flex-1 flex flex-col min-w-0">
  {/* PRHeader -- unchanged */}
  {isEmpty ? <PRHeaderEmpty /> : <PRHeader ... />}

  {/* NEW: Content tab bar */}
  {!isEmpty && contentTab && onContentTabChange && (
    <ContentTabBar
      activeTab={contentTab}
      onTabChange={onContentTabChange}
      diffFileCount={diffFileCount}
      browserUrl={browserUrl}
      onBrowserUrlChange={onBrowserUrlChange}
      onBrowserUrlSubmit={onBrowserUrlSubmit}
    />
  )}

  {/* Content viewport -- unchanged structure, children now tab-driven */}
  <div className="flex-1 overflow-auto">
    {children}
  </div>
</main>
```

#### Files summary

| File | Action |
|------|--------|
| `src/App.tsx` | Modify (add contentTab state, change content switching, fix useFileContent gating, iframe persist) |
| `src/components/templates/AppShell/AppShell.tsx` | Modify (add ContentTabBar, new props, conditional PRHeader toolbar) |

---

### Phase 3: BrowserPanel organism + UrlInput atom

Build the embedded browser panel.

#### File: `app/frontend/src/components/organisms/BrowserPanel/BrowserPanel.tsx` (new)

Structure:
```tsx
function BrowserPanel({ url, onNavigate, onLoad, onError }: BrowserPanelProps) {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Reset loading state when URL changes
  useEffect(() => {
    setLoading(true);
    setLoadError(false);
  }, [url]);

  return (
    <div className="relative w-full h-full bg-[var(--bg-canvas)]">
      {loading && <LoadingOverlay />}
      {loadError ? (
        <BrowserErrorState url={url} />
      ) : (
        <iframe
          ref={iframeRef}
          src={url}
          className="w-full h-full border-0"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          onLoad={() => { setLoading(false); onLoad?.(); }}
          onError={() => { setLoading(false); setLoadError(true); onError?.("Failed to load"); }}
        />
      )}
    </div>
  );
}
```

Internal components (in the same file, not exported):
- `LoadingOverlay`: centered spinner/skeleton over the iframe area, absolute positioned, fades out on load
- `BrowserErrorState`: centered message showing the URL, an explanation that the site may block embedding, and a "Open in new tab" link (`<a href={url} target="_blank">`)

#### File: `app/frontend/src/components/organisms/BrowserPanel/index.ts` (new)

Barrel export.

#### File: `app/frontend/src/components/organisms/index.ts` (modify)

Add `BrowserPanel` export.

#### Files summary

| File | Action |
|------|--------|
| `src/components/organisms/BrowserPanel/BrowserPanel.tsx` | Create |
| `src/components/organisms/BrowserPanel/index.ts` | Create |
| `src/components/organisms/index.ts` | Modify |

---

### Phase 4: Keyboard shortcuts + polish

#### File: `app/frontend/src/App.tsx` (modify)

Add a `useEffect` in `AuthenticatedApp` that listens for keyboard shortcuts:

```ts
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    const mod = e.metaKey || e.ctrlKey;
    if (mod && e.shiftKey && e.key === "1") { e.preventDefault(); setContentTab("diffs"); }
    if (mod && e.shiftKey && e.key === "2") { e.preventDefault(); setContentTab("code"); }
    if (mod && e.shiftKey && e.key === "3") { e.preventDefault(); setContentTab("browser"); }
    if (mod && e.key === "l" && contentTab === "browser") {
      e.preventDefault();
      // Focus the URL input -- requires ref forwarding from ContentTabBar
    }
  };
  window.addEventListener("keydown", handler);
  return () => window.removeEventListener("keydown", handler);
}, [contentTab]);
```

#### Polish items

- Add `aria-label` attributes to the tab bar for accessibility
- Add a subtle transition when switching tabs (opacity fade, 100ms)
- Persist `browserUrl` across tab switches (already handled by state living in AuthenticatedApp)
- Iframe mount/persist is handled in Phase 2 via `hasActivatedBrowser` + `display: none` (not deferred to Phase 4)

#### File: `app/frontend/src/components/molecules/ContentTabBar/ContentTabBar.tsx` (modify)

Add `urlInputRef` forwarding for Cmd+L focus support.

#### Files summary

| File | Action |
|------|--------|
| `src/App.tsx` | Modify (keyboard shortcuts) |
| `src/components/molecules/ContentTabBar/ContentTabBar.tsx` | Modify (ref forwarding) |

## Complete File Tree

```
app/frontend/src/
  types/
    content.ts                                      [create] ContentTab type
    sidebar.ts                                      [no change] SidebarMode stays as-is
  components/
    atoms/
      Icon/
        Icon.tsx                                    [modify] Add globe + code icons
      UrlInput/
        UrlInput.tsx                                [create] Compact URL input
        index.ts                                    [create] Barrel export
      index.ts                                      [modify] Export UrlInput
    molecules/
      ContentTabBar/
        ContentTabBar.tsx                           [create] Tab bar for main content
        index.ts                                    [create] Barrel export
      index.ts                                      [modify] Export ContentTabBar
    organisms/
      BrowserPanel/
        BrowserPanel.tsx                            [create] Iframe-based web viewer
        index.ts                                    [create] Barrel export
      index.ts                                      [modify] Export BrowserPanel
    templates/
      AppShell/
        AppShell.tsx                                [modify] Insert ContentTabBar, new props
  App.tsx                                           [modify] Add contentTab state, keyboard shortcuts
```

**Summary:** 7 new files, 6 modified files, 0 deleted files.

## Future Direction: Native macOS via Tauri

The iframe approach is intentionally simple and works today. When Stack Bench moves to a Tauri desktop app:

1. **BrowserPanel becomes the swap point.** Replace the `<iframe>` with Tauri's `<webview>` component (backed by WKWebView on macOS). The component interface (`url`, `onNavigate`, `onLoad`, `onError`) remains identical -- the swap is internal to `BrowserPanel`.

2. **WKWebView advantages.** No CORS/X-Frame-Options restrictions. Full DevTools access. Native scrolling. Cookie isolation. Better performance for heavy pages.

3. **No architectural changes needed.** The tab system, URL bar, keyboard shortcuts, and state management all remain the same. Only the BrowserPanel internals change.

4. **Progressive enhancement.** Detect the runtime environment (`window.__TAURI__` exists) and render the native webview when available, falling back to iframe in web mode. This lets the same codebase work in both contexts.

## Testing Strategy

**Visual verification (primary -- via `/verify`):**
- Tab bar renders with three tabs, "Stack Diffs" active by default
- Clicking tabs switches content correctly
- Browser tab shows URL input inline when active
- Entering a URL loads the page in the iframe
- Iframe loading shows spinner, then content
- Sites that block framing show error state with "Open in new tab" link
- Keyboard shortcuts switch tabs correctly
- Cmd+L focuses URL bar on Browser tab
- Layout remains stable (no height jumps, no scroll resets) when switching tabs
- Sidebar mode toggle still works independently of content tabs

**Render smoke tests** (test file paths):
- `__tests__/components/atoms/UrlInput.test.tsx` -- renders, handles Enter key submission
- `__tests__/components/molecules/ContentTabBar.test.tsx` -- renders three tabs, shows URL input on browser tab, fires onTabChange
- `__tests__/components/organisms/BrowserPanel.test.tsx` -- renders with valid URL, shows error/hint state

**Integration scenarios:**
- [ ] Load app, verify default is Diffs tab with diff content
- [ ] Switch to Code tab, verify FileContent renders for selected file
- [ ] Switch to Browser tab, verify URL input appears and iframe renders
- [ ] Navigate to a URL, switch to Diffs tab, switch back -- page is still loaded (not reloaded)
- [ ] Cmd+1/2/3 switches tabs correctly
- [ ] Sidebar Diffs/Files toggle does not affect content tab
- [ ] Content tab does not affect sidebar tree display

## Open Questions

1. **Should clicking a file in the sidebar auto-switch to the Code tab?** Two options: (a) always switch to Code tab when a file is clicked in the sidebar, or (b) only switch when already on the Code tab, and on other tabs just update `selectedPath` silently. Option (b) is less disruptive but may confuse users who expect to see the file they clicked. Recommendation: option (a) with a brief "viewing file" toast or visual cue.

2. **Should the Browser tab persist its URL in the URL bar / localStorage?** Currently planned as ephemeral state in `AuthenticatedApp`. For cross-session persistence, we could save the last URL to localStorage keyed by stack ID.

3. ~~**Should the PRHeader toolbar (expand/collapse all, comment mode) only show on the Diffs tab?**~~ **Resolved: Yes.** The PRHeader toolbar is diff-specific and must only render when `contentTab === "diffs"`. This is handled in Phase 2 (step 7).

4. **Should we pre-populate the browser URL from the PR's deployment URL?** If the backend exposes a deployment/preview URL for the active branch's PR, the Browser tab could auto-navigate there. This is a natural follow-up but out of scope for this spec.

5. **Content Security Policy.** The app itself may need a CSP `frame-src` directive to allow the iframe to load external URLs. This depends on how the frontend is served (Vite dev server vs. production Nginx). Vite dev server is permissive by default. Production Nginx may need a header update.
