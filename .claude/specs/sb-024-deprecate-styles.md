# SB-024: Deprecate ui/styles.go

**Status:** draft
**Issue:** SB-024
**Date:** 2026-03-24

## Summary

Remove the legacy convenience style variables (`Dim`, `Fg`, `Bold`, `Green`, `Red`, `Accent`) and the unused `MaxI` helper from `app/cli/internal/ui/styles.go`. All callers will be migrated to use `theme.Resolve()` or direct `theme.Active()` field access.

## What Is Being Removed

File: `app/cli/internal/ui/styles.go`

```go
var (
    Dim    = lipgloss.NewStyle().Foreground(theme.Active().DimColor)
    Fg     = lipgloss.NewStyle().Foreground(theme.Active().Foreground)
    Bold   = lipgloss.NewStyle().Bold(true).Foreground(theme.Active().Foreground)
    Green  = theme.Resolve(theme.Style{Status: theme.Success})
    Red    = theme.Resolve(theme.Style{Status: theme.Error})
    Accent = theme.Resolve(theme.Style{Category: theme.CatAgent})
)

func MaxI(a, b int) int { ... }
```

`RefreshStyles()` is mentioned in the issue but does not exist in the current file -- it was already removed.

`MaxI` has zero callers and can be deleted with the file. Go's built-in `max()` (Go 1.21+) is the replacement if needed.

## Migration Map

Each legacy var maps to a `theme.Resolve()` call or direct `theme.Active()` access:

| Legacy Var   | Replacement |
|-------------|-------------|
| `ui.Dim`    | `theme.Resolve(theme.Style{Emphasis: theme.Subtle})` -- or inline `lipgloss.NewStyle().Foreground(theme.Active().DimColor)` |
| `ui.Fg`     | `theme.Resolve(theme.Style{})` -- default foreground |
| `ui.Bold`   | `theme.Resolve(theme.Style{Emphasis: theme.Strong})` |
| `ui.Green`  | `theme.Resolve(theme.Style{Status: theme.Success})` |
| `ui.Red`    | `theme.Resolve(theme.Style{Status: theme.Error})` |
| `ui.Accent` | `theme.Resolve(theme.Style{Category: theme.CatAgent})` |

**Note on `Dim`:** `theme.Resolve` with `Emphasis: Subtle` only applies DimColor when `Category == CatDefault` (which is the zero value, i.e., `CatAgent`). This means the Subtle path in `theme.Resolve` does NOT produce the same result as the legacy `Dim` -- it would apply `CatAgent` color instead of `DimColor`. The safest replacement for `Dim` is the inline form: `lipgloss.NewStyle().Foreground(theme.Active().DimColor)`. Alternatively, add a `Tertiary` hierarchy usage or a dedicated helper. See Risk Assessment below.

**Recommended approach:** Define convenience functions on the theme package to keep call sites clean.

## Callers -- Complete List

### 1. `app/cli/internal/ui/markdown.go` (intra-package)

Line 220: `Dim.Render("| ")` -- blockquote border rendering.

This is within the `ui` package itself, so it references `Dim` without the `ui.` prefix. Must be migrated before the file is deleted or the package won't compile.

**Migration:** Replace with `lipgloss.NewStyle().Foreground(theme.Active().DimColor).Render("| ")` or a local var.

### 2. `app/cli/internal/app/model.go`

Uses: `ui.Bold`, `ui.Dim`, `ui.Red`, `ui.Green`, `ui.Fg`, `ui.Accent` (all six vars).

Occurrences (by line):
- 213: `ui.Bold.Render(" STACK BENCH")` -- title
- 215: `ui.Dim.Render(strings.Repeat("-", m.width))` -- separator
- 219: `ui.Red.Render(...)` -- error display
- 221: `ui.Dim.Render("  Press q to quit.")` -- hint text
- 223: `ui.Dim.Render("  Loading agents...")` -- loading text
- 225: `ui.Fg.Render("  Select an agent...")` -- body text
- 231: `ui.Accent.Render("> ")` -- cursor
- 234: `ui.Fg.Render(agent.Name)` -- agent name
- 236: `ui.Bold.Render(agent.Name)` -- selected agent name
- 239: `ui.Dim.Render(agent.Role)` -- role metadata
- 272: `ui.Green.Render("*")` + `ui.Dim.Render(" backend")` -- healthy indicator
- 274: `ui.Red.Render("*")` + `ui.Dim.Render(" backend")` -- unhealthy indicator
- 276-278: `ui.Dim.Render("o backend")` -- starting/default indicator
- 282: `ui.Dim.Render(strings.Repeat("-", m.width))` -- separator
- 284: `ui.Dim.Render(" " + hint)` -- status bar hint

**Migration:** Add `import "github.com/dugshub/stack-bench/app/cli/internal/ui/theme"` (if not present), replace all `ui.X` with `theme.Resolve(...)` calls. The `ui` import can be removed entirely (no `ui.RenderMarkdown` usage here).

### 3. `app/cli/internal/chat/view.go`

Uses: `ui.Bold`, `ui.Dim`, `ui.Fg`, `ui.Accent`.

Already imports `theme` in addition to `ui`. Occurrences:
- 53: `ui.Bold.Render("CHAT")` -- header title
- 57: `ui.Dim.Render("agent: ")` + `ui.Accent.Render(agent)` -- metadata
- 59: `ui.Dim.Render(fmt.Sprintf(...))` -- exchange count
- 62: `ui.Accent.Render("[branch]")` -- branch indicator
- 64: `ui.Dim.Render("  ")` -- separator between meta items
- 71: `ui.Dim.Render(strings.Repeat("-", m.width))` -- separator
- 77: `ui.Dim.Render("  No messages yet...")` -- empty state
- 91: `ui.Accent.Render("  ...")` -- streaming indicator
- 128: `ui.Dim.Render("you:")` + `ui.Fg.Render(msg.Content)` -- user message
- 130: `ui.Accent.Render("sb:")` -- assistant prefix
- 152: `ui.Dim.Render(strings.Repeat("-", m.width))` -- prompt separator
- 154: `ui.Dim.Render("you:")` + `ui.Fg.Render(cursor)` -- prompt

**Migration:** Already has `theme` import. Replace `ui.X` with `theme.Resolve(...)`. Keep `ui` import for `ui.RenderMarkdown` (line 135).

### 4. `app/cli/internal/chat/picker.go`

Uses: `ui.Bold`, `ui.Dim`, `ui.Fg`, `ui.Accent`, `ui.Red`.

Does NOT currently import `theme`. Occurrences:
- 127-129: header -- Bold title, Dim separator, Accent agent name
- 131: `ui.Dim.Render(strings.Repeat("-", m.width))` -- separator
- 135: `ui.Red.Render(...)` -- error
- 137: `ui.Dim.Render("  Loading conversations...")` -- loading
- 141: `ui.Fg.Render("+ New conversation")` -- list item
- 143: `ui.Accent.Render("> ")` -- cursor
- 144: `ui.Bold.Render("+ New conversation")` -- selected item
- 150: `ui.Dim.Render("  Past conversations:")` -- section label
- 157: `ui.Accent.Render("> ")` -- cursor
- 163: `ui.Bold.Render(label)` -- selected label
- 165: `ui.Fg.Render(label)` -- unselected label
- 176: `ui.Accent.Render("[branch]")` -- branch indicator
- 180: `ui.Dim.Render(meta)` -- conversation metadata
- 184: `ui.Dim.Render("  No past conversations.")` -- empty state

**Migration:** Add `theme` import, replace all `ui.X` with `theme.Resolve(...)`. The `ui` import can be removed entirely (no other `ui.` usage).

## Order of Operations

1. **Decide on Dim replacement strategy** -- either:
   - (a) Add `theme.Dim()`, `theme.Fg()`, `theme.Bold()` convenience functions to `registry.go`, or
   - (b) Use inline `theme.Resolve(...)` everywhere (verbose but explicit), or
   - (c) Define file-local `var dim = ...` in each caller (reduces import noise but duplicates)

   Recommendation: Option (a) -- add a small set of convenience functions to `theme/registry.go`:
   ```go
   func Dim() lipgloss.Style  { return lipgloss.NewStyle().Foreground(active.DimColor) }
   func Fg() lipgloss.Style   { return lipgloss.NewStyle().Foreground(active.Foreground) }
   func Bold() lipgloss.Style { return lipgloss.NewStyle().Bold(true).Foreground(active.Foreground) }
   ```
   This keeps call sites clean (`theme.Dim().Render(...)`) and avoids the `Resolve` semantic mismatch for Dim.

2. **Migrate `ui/markdown.go`** (line 220) -- intra-package reference, must happen before deletion.

3. **Migrate `app/model.go`** -- heaviest user (15+ call sites). Remove `ui` import afterward.

4. **Migrate `chat/view.go`** -- keep `ui` import for `RenderMarkdown`.

5. **Migrate `chat/picker.go`** -- remove `ui` import entirely.

6. **Delete `app/cli/internal/ui/styles.go`**.

7. **Verify build** -- `cd app/cli && go build ./...`

## Risk Assessment

**Low risk overall** -- this is a mechanical find-and-replace with known callers.

| Risk | Severity | Mitigation |
|------|----------|------------|
| `Dim` via `theme.Resolve` does not match legacy behavior | Medium | The `Subtle` emphasis path in `Resolve` checks `CatDefault` which equals `CatAgent` (iota 0), not a true "default" category. Using `Resolve(Style{Emphasis: Subtle})` would get CatAgent color, not DimColor. Use direct `theme.Active().DimColor` or add convenience functions instead. |
| `CatDefault` is referenced in `theme.go:45` but undefined in `tokens.go` | Low | Pre-existing issue (compiles because Go treats it as zero value = CatAgent). Not blocking for SB-024 but should be tracked separately. |
| Missed caller breaks build | Low | Full grep covers `ui.Dim`, `ui.Fg`, `ui.Bold`, `ui.Green`, `ui.Red`, `ui.Accent` across the entire `app/cli` tree, plus intra-package bare names in `ui/`. No other callers exist. |
| `MaxI` removal breaks something | None | Zero callers found. |

## Testing Strategy

1. After each file migration, run `cd /Users/dug/Projects/stack-bench/app/cli && go build ./...` to verify compilation.
2. After all migrations and deletion, run `go vet ./...` for additional static checks.
3. Run `just test` from the project root (if CLI tests exist) to verify no runtime regressions.
4. Grep the full tree one final time for any `"internal/ui"` imports that no longer need the `ui` package.
