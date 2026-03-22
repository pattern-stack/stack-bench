---
title: Shiki Syntax Highlighting for Diff Viewer
status: draft
created: 2026-03-21
stack: frontend-mvp
stack_index: 6
---

# Shiki Syntax Highlighting for Diff Viewer

## Summary

Add language-aware syntax highlighting to the diff viewer using [Shiki](https://shiki.style). Code content in diff lines gets highlighted while preserving the existing add/del/context/hunk background colors, +/- prefixes, and line numbers.

## Current State

- `DiffLine` (atom) renders plain text with `+`/`-` prefix and background color per line type
- `DiffHunk` (molecule) renders a hunk header + array of DiffLines
- `DiffFile` (molecule) renders a collapsible header + array of DiffHunks
- `FilesChangedPanel` (organism) renders file list + DiffFiles
- `DiffLine.content` is a raw string — no HTML, no tokens

## Approach: Highlight at Hook Level, Render Tokens in Atom

### Why not highlight per-line?

Shiki needs the full file context (or at minimum a contiguous block) to produce correct tokenization. Highlighting individual lines would break multi-line strings, comments, and nested structures. Also, creating a highlighter instance per line would be wasteful.

### Strategy

1. **New hook `useHighlightedDiff`** — takes a `DiffFile` (with its `path` and all line contents), extracts both the "old" and "new" file content by reassembling lines, highlights them as complete documents via Shiki, then maps highlighted tokens back to each `DiffLine`.

2. **Extended type `HighlightedDiffLine`** — `DiffLine` plus an optional `highlightedHtml: string` field containing the Shiki-generated HTML for the code portion only (no prefix, no line numbers).

3. **DiffLine atom** — gains an optional `highlightedHtml` prop. When present, renders it via `dangerouslySetInnerHTML` instead of plain text. When absent, falls back to plain text (graceful degradation).

4. **DiffFile molecule** — calls `useHighlightedDiff` and passes enriched lines down through DiffHunks.

## Language Detection

New utility `lib/lang-from-path.ts`:

```ts
const EXT_MAP: Record<string, string> = {
  ts: "typescript", tsx: "tsx", js: "javascript", jsx: "jsx",
  py: "python", go: "go", rs: "rust", rb: "ruby",
  css: "css", scss: "scss", html: "html", json: "json",
  yaml: "yaml", yml: "yaml", md: "markdown", sh: "bash",
  sql: "sql", graphql: "graphql", toml: "toml",
  // Fallback handled by returning undefined
};

export function langFromPath(path: string): string | undefined {
  const ext = path.split(".").pop()?.toLowerCase();
  return ext ? EXT_MAP[ext] : undefined;
}
```

When `langFromPath` returns `undefined`, skip highlighting entirely — DiffLine renders plain text.

## Theme

Use Shiki's built-in `github-dark` theme. It's the closest match to our design tokens (same color family as GitHub's dark mode which our tokens are derived from). The Shiki-generated `<span>` elements will have inline `color` styles from the theme — these blend naturally with our `--fg-default` base.

No custom theme needed initially. The background colors from `--green-bg`, `--red-bg`, etc. are applied by DiffLine's wrapper `<div>`, not by Shiki, so there's no conflict.

If the colors feel off, we can create a custom theme later by overriding `github-dark` token colors to exactly match our design tokens.

## Performance

1. **Singleton highlighter** — Create one `Highlighter` instance via `createHighlighter()` on first use, cache it in module scope. Subsequent calls reuse it.

2. **Lazy language loading** — Use `shiki/bundle/web` which tree-shakes unused languages. Only load grammars for languages actually present in the diff via `highlighter.loadLanguage()`.

3. **Async highlighting with suspense-friendly pattern** — `useHighlightedDiff` returns `{ lines, loading }`. On first render, lines are plain (unhighlighted). Once Shiki initializes and highlights, re-render with highlighted HTML. This avoids blocking the initial diff render.

4. **Memoization** — `useMemo` keyed on `file.path` + line contents to avoid re-highlighting on unrelated re-renders.

5. **Skip unchanged files** — Only highlight files whose hunks are currently expanded (visible).

## Bundle Impact

| Bundle | Size (gzip) | Notes |
|--------|-------------|-------|
| `shiki` full | ~6MB | All 200+ languages — too large |
| `shiki/bundle/web` | ~1.5MB | ~40 common web languages — good fit |
| Per-language grammar | ~10-50KB each | Loaded lazily on demand |
| `github-dark` theme | ~8KB | Single theme, loaded once |

**Recommendation**: Use `shiki/bundle/web`. It includes TypeScript, JavaScript, CSS, JSON, Python, Go, Rust, and other languages common in our diff context. Estimated additional bundle cost: **~200KB gzip** (base WASM engine + theme + common grammars via code splitting).

## Files to Create

| File | Layer | Purpose |
|------|-------|---------|
| `src/lib/lang-from-path.ts` | Utility | Map file extension → Shiki language ID |
| `src/lib/shiki.ts` | Utility | Singleton highlighter factory, highlight function |
| `src/hooks/useHighlightedDiff.ts` | Hook | Highlight a DiffFile's lines, return enriched data |

## Files to Modify

| File | Change |
|------|--------|
| `src/types/diff.ts` | Add optional `highlightedHtml` to `DiffLine` |
| `src/components/atoms/DiffLine/DiffLine.tsx` | Accept + render `highlightedHtml` prop |
| `src/components/molecules/DiffFile/DiffFile.tsx` | Call `useHighlightedDiff`, pass enriched lines to hunks |
| `src/components/molecules/DiffHunk/DiffHunk.tsx` | Pass through enriched line data (minimal change) |

## Detailed Component Changes

### `DiffLine` (atom)

```tsx
// Add to DiffLineAtomProps:
highlightedHtml?: string;

// In the content span, replace:
{isHunk ? line.content : `${prefixMap[line.type]}${line.content}`}

// With:
{isHunk ? (
  line.content
) : (
  <>
    {prefixMap[line.type]}
    {highlightedHtml ? (
      <span dangerouslySetInnerHTML={{ __html: highlightedHtml }} />
    ) : (
      line.content
    )}
  </>
)}
```

The atom stays pure — it receives pre-computed HTML and renders it. No Shiki dependency.

### `DiffHunk` (molecule)

Minimal change: accept an optional map of highlighted HTML keyed by line index, pass through to DiffLine.

```tsx
interface DiffHunkMoleculeProps {
  hunk: DiffHunkType;
  highlightedLines?: Map<number, string>; // globalLineIndex → html
  lineOffset?: number; // offset into the global line list
}
```

Actually, simpler approach: enrich the `DiffLine` data directly before passing to DiffHunk, so DiffHunk needs no changes at all if we extend the `DiffLine` type.

### `DiffFile` (molecule → uses hook)

```tsx
function DiffFileMolecule({ file }: DiffFileMoleculeProps) {
  const [expanded, setExpanded] = useState(true);
  const { highlightedHunks } = useHighlightedDiff(file, expanded);

  return (
    <Collapsible open={expanded} onOpenChange={setExpanded}>
      <CollapsibleTrigger asChild>
        <DiffFileHeader file={file} expanded={expanded} onToggle={() => setExpanded(!expanded)} />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="...">
          {highlightedHunks.map((hunk, i) => (
            <DiffHunkMolecule key={i} hunk={hunk} />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
```

Note: DiffFile is a molecule that now calls a hook. Per the atomic design rules, molecules can use `useState`/`useRef` for local state. Using a custom hook that manages highlighting state is acceptable here since the hook serves the molecule's single concern (rendering a diff file). If this feels like a violation, the hook call can be lifted to FilesChangedPanel (organism) instead.

### `useHighlightedDiff` hook

```ts
export function useHighlightedDiff(file: DiffFile, enabled: boolean) {
  // 1. Detect language from file.path
  // 2. If no language or not enabled, return hunks as-is
  // 3. Reassemble "old" lines (context + del) and "new" lines (context + add)
  // 4. Highlight both via getHighlighter()
  // 5. Map highlighted tokens back to each DiffLine position
  // 6. Return hunks with highlightedHtml set on each line
}
```

### `shiki.ts` singleton

```ts
import { createHighlighter, type Highlighter } from "shiki/bundle/web";

let highlighterPromise: Promise<Highlighter> | null = null;

export function getHighlighter(): Promise<Highlighter> {
  if (!highlighterPromise) {
    highlighterPromise = createHighlighter({
      themes: ["github-dark"],
      langs: [], // load on demand
    });
  }
  return highlighterPromise;
}

export async function highlightCode(code: string, lang: string): Promise<string[]> {
  const h = await getHighlighter();
  // Ensure language is loaded
  if (!h.getLoadedLanguages().includes(lang)) {
    await h.loadLanguage(lang as any);
  }
  // Use codeToTokens for line-by-line token access
  const { tokens } = h.codeToTokens(code, { lang, theme: "github-dark" });
  // Convert each line's tokens to an HTML string
  return tokens.map((lineTokens) =>
    lineTokens
      .map((t) => `<span style="color:${t.color}">${escapeHtml(t.content)}</span>`)
      .join("")
  );
}
```

## CSS Considerations

Shiki's inline `<span style="color:...">` elements render inside DiffLine's content area. The existing classes handle:
- Background color (`bg-[var(--green-bg)]` etc.) — on the wrapper div, unaffected
- Font (`font-[family-name:var(--font-mono)]`) — inherited by Shiki spans
- Text color (`text-[var(--fg-default)]`) — overridden by Shiki's inline styles, which is correct

No additional CSS needed. The `whitespace-pre` on the content span preserves indentation.

## Edge Cases

1. **Binary files** — no content lines, no highlighting needed
2. **Unknown language** — `langFromPath` returns undefined, skip highlighting
3. **Very large files** — highlight async, show plain text while loading
4. **Renamed files** — use new path for language detection
5. **Mixed hunks** — each line is independently mapped; context lines appear in both old/new so they get consistent highlighting

## Git / Stack Strategy

This work belongs to the **frontend-mvp** stack. Current branch is `dugshub/frontend-mvp/5-diff`.

**Preferred approach:** Create a new branch `dugshub/frontend-mvp/6-syntax-highlighting` via:

```bash
stack branch insert
```

This keeps the diff viewer commit (5-diff) clean and makes syntax highlighting a reviewable, revertible unit on top of it.

**Alternative:** If the changes are small enough, amend into `5-diff`. Use the new branch approach by default.

## Implementation Order

1. Create stack branch: `stack branch insert` → `6-syntax-highlighting`
2. Install `shiki` dependency
3. Create `lib/lang-from-path.ts`
4. Create `lib/shiki.ts` (singleton + highlight function)
5. Add `highlightedHtml` to `DiffLine` type
6. Create `hooks/useHighlightedDiff.ts`
7. Update `DiffLine` atom to render highlighted HTML
8. Update `DiffFile` molecule to use the hook
9. Test with mock data (TypeScript, CSS, JSON files in mock-diff-data)
