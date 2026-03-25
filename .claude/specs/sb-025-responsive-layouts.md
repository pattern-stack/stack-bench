# SB-025: Responsive Component Layouts for Narrow Terminals

**Status:** draft
**Issue:** SB-025
**Date:** 2026-03-24
**Depends on:** SB-024 (deprecate styles.go -- completed)

## Summary

Components clip and overflow at narrow terminal widths (~78px and below). This spec adds a breakpoint system to `RenderContext` via a `Compact()` method, then updates each non-code, non-table component to gracefully condense down to ~50px without losing functionality.

## Breakpoint System Design

### RenderContext Changes

Add a single method to the existing `RenderContext` struct in `atoms/atoms.go`:

```go
// Compact reports whether the current width is below the compact threshold.
// Components should use this to switch to condensed layouts.
func (ctx RenderContext) Compact() bool {
    return ctx.Width > 0 && ctx.Width < CompactThreshold
}
```

Add the threshold constant in the same file:

```go
// CompactThreshold is the width (in columns) below which components
// switch to compact layout. Discovered through testing; start at 72.
const CompactThreshold = 72
```

**Why 72:** Standard terminal widths are 80 and 120. At 80, the chat view's `contentWidth` is `width - 4 = 76`, and molecule components render within that. Below ~72, badge rows and inline tool call headers start clipping. 72 gives a few columns of breathing room before the 80-column edge case. The constant is exported so it can be tuned in one place after visual testing.

**Why a method, not a field:** `Compact()` is derived from `Width`, so storing it separately would create a consistency risk. A method keeps `RenderContext` a two-field struct (Width + Theme) while giving components a clean boolean to branch on.

### What Does NOT Change

- `RenderContext` stays a value type (no pointer, no interface).
- `DefaultContext(width)` signature is unchanged.
- The `molecules.RenderContext` type alias continues to work with no changes.
- Components that already handle width correctly (CodeBlock, Separator) are untouched.

## Per-Component Compact Layout Changes

### 1. StatusBlock (molecule) -- `molecules/statusblock.go`

**Normal layout (width >= 72):**
```
[spinner] Syncing [5s] [3/7]
```

**Compact layout (width < 72):**
Drop the elapsed and count badges. The verb and spinner are sufficient to convey status in tight spaces.

```
[spinner] Syncing
```

**Implementation:** In `View()`, wrap the elapsed and count badge blocks with `if !ctx.Compact()`:

```go
if !ctx.Compact() {
    if sb.Data.Elapsed != "" {
        parts = append(parts, atoms.Badge(ctx, atoms.BadgeData{...}))
    }
    if sb.Data.Count != "" {
        parts = append(parts, atoms.Badge(ctx, atoms.BadgeData{...}))
    }
}
```

### 2. ConfirmPrompt (molecule) -- not yet implemented (SB-023)

**Normal layout:**
```
Allow file edit?
[Yes]  No
```

**Compact layout:**
Stack the options below the question on their own line, left-aligned. The options row already wraps naturally since it is a `strings.Join` of badges -- no structural change needed beyond ensuring it does not exceed width. However, at very narrow widths the question text itself may wrap, so the options should appear on a separate line regardless. The key compact behavior: reduce inter-option spacing from two spaces to one.

```
Allow file edit?
[Yes] No
```

**Implementation note:** Since SB-023 is not yet implemented, this behavior should be built into the initial implementation. The spec for SB-023 should reference `ctx.Compact()` for spacing. If SB-023 lands first, a follow-up modification applies the compact spacing. If SB-025 lands first, SB-023 picks up the pattern.

### 3. ToolCallPart (chat view) -- `chat/view.go`

**Normal layout:**
```
tool: Read  done
```

**Compact layout:**
Stack the tool name and status vertically:

```
tool: Read
  done
```

**Implementation:** In `renderToolCallPart()`, create a `RenderContext` from the width parameter and check `Compact()`:

```go
ctx := atoms.DefaultContext(width)
if ctx.Compact() {
    header = theme.Dim().Render("tool: ") + theme.Fg().Render(p.Name) + "\n  " + status
} else {
    header = theme.Dim().Render("tool: ") + theme.Fg().Render(p.Name) + "  " + status
}
```

### 4. Chat Header (chat view) -- `chat/view.go`

**Normal layout:**
```
 CHAT                          agent: builder  3 exchanges  [branch]
--------------------------------------------------------------------
```

**Compact layout:**
Drop the exchange count and branch indicator. Keep only the title and agent name.

```
 CHAT                 agent: builder
--------------------------------------
```

**Implementation:** In `renderHeader()`, gate the optional metadata on a compact check:

```go
ctx := atoms.DefaultContext(m.width)
meta = append(meta, theme.Dim().Render("agent: ") + theme.Resolve(...).Render(agent))
if !ctx.Compact() {
    if m.ExchangeCount > 0 {
        meta = append(meta, ...)
    }
    if m.IsBranch {
        meta = append(meta, ...)
    }
}
```

When `fill` computes to negative (right side wider than available space), the current code clamps to 0 but the line still overflows. With compact mode dropping metadata, this becomes much less likely. As a safety net, if `fill < 0` the right-side metadata should be truncated (existing behavior is acceptable for now).

### 5. App Status Bar -- `app/model.go`

**Normal layout:**
```
--------------------------------------------------------------------
 j/k: navigate  enter: select  q: quit                    * backend
```

**Compact layout:**
Drop the health indicator. The hint text is sufficient.

```
--------------------------------------
 j/k: navigate  enter: select  q: quit
```

**Implementation:** In `renderStatus()`, gate the health indicator:

```go
ctx := atoms.DefaultContext(m.width)
if !ctx.Compact() && m.manager != nil {
    // build healthIndicator
}
```

### Components NOT Changed

| Component | Reason |
|-----------|--------|
| CodeBlock | Truncates by design (out of scope) |
| Table | Truncates by design (out of scope) |
| Badge | Already has MaxWidth truncation; no layout change needed |
| TextBlock | Already respects ctx.Width for wrapping |
| Separator | Uses full ctx.Width; inherently responsive |
| Spinner | Single character; no layout concern |
| Icon | Single character; no layout concern |
| InlineCode | Inline span; no layout concern |

## Implementation Steps

### Step 1: Add Compact() to RenderContext

File: `app/cli/internal/ui/components/atoms/atoms.go`

1. Add `CompactThreshold` constant (72).
2. Add `Compact()` method on `RenderContext`.
3. Add tests in `atoms_test.go`:
   - `TestCompactBelowThreshold` -- width 50 returns true
   - `TestCompactAtThreshold` -- width 72 returns false
   - `TestCompactAboveThreshold` -- width 80 returns false
   - `TestCompactZeroWidth` -- width 0 returns false (zero-width contexts are inline, not compact)

### Step 2: Update StatusBlock

File: `app/cli/internal/ui/components/molecules/statusblock.go`

1. Gate elapsed and count badges on `!ctx.Compact()`.
2. Add tests in `statusblock_test.go`:
   - `TestStatusBlockCompactOmitsElapsed` -- width 50, elapsed set, output does not contain elapsed text
   - `TestStatusBlockCompactOmitsCount` -- width 50, count set, output does not contain count text
   - `TestStatusBlockCompactKeepsVerb` -- width 50, output still contains verb text
   - `TestStatusBlockNormalShowsAll` -- width 80, all parts present (existing tests cover this, but an explicit compact-vs-normal pair is clearer)

### Step 3: Update renderToolCallPart

File: `app/cli/internal/chat/view.go`

1. Create a `RenderContext` from the width parameter.
2. Use `ctx.Compact()` to choose between inline and stacked layout for the tool name + status line.
3. Add tests in `chat/view_test.go` (create if needed):
   - `TestToolCallPartCompactStacks` -- narrow width, output contains newline between name and status
   - `TestToolCallPartNormalInline` -- wide width, name and status on same line

### Step 4: Update renderHeader

File: `app/cli/internal/chat/view.go`

1. Create a `RenderContext` and gate exchange count / branch metadata on `!ctx.Compact()`.
2. Add tests:
   - `TestHeaderCompactDropsMetadata` -- narrow width, output does not contain "exchanges" or "[branch]"
   - `TestHeaderNormalShowsMetadata` -- wide width, both present

### Step 5: Update renderStatus

File: `app/cli/internal/app/model.go`

1. Gate health indicator on `!ctx.Compact()`.
2. Add tests:
   - `TestStatusBarCompactDropsHealth` -- narrow width, output does not contain health indicator

### Step 6: Verify

```bash
go test ./... && go vet ./...
```

All existing tests continue to pass (they use width 80, which is above the threshold). New tests validate compact behavior.

## Testing Strategy

### Unit Tests

Every component gets paired tests: one at a wide width (80) confirming normal layout, one at a narrow width (50) confirming compact layout. Tests use `strings.Contains` / `!strings.Contains` to check for presence or absence of specific text (badge content, metadata strings). No snapshot tests.

### Manual Visual Testing

After implementation, resize a terminal to various widths and visually confirm:

| Width | Expected Behavior |
|-------|-------------------|
| 120 | Full layout, all metadata, all badges |
| 80 | Full layout (above threshold) |
| 72 | Full layout (at threshold, not compact) |
| 71 | Compact kicks in -- badges drop, tool calls stack |
| 60 | Compact layout, everything still readable |
| 50 | Compact layout at minimum target width |
| 49 | Below target -- degradation acceptable |

### Threshold Tuning

The `CompactThreshold` constant (starting at 72) should be adjusted based on visual testing. The value is in one place (`atoms.go`) so it can be changed without touching any component logic. If testing reveals that different components need different thresholds, the system can be extended to multiple named breakpoints later -- but start with one.

## Open Questions

1. **Should `Compact()` be a method or a standalone function?** Method is recommended (keeps the API on the context object). A standalone `atoms.IsCompact(width)` would also work but adds a function where a method reads more naturally (`ctx.Compact()`).

2. **Future breakpoints:** If a second breakpoint is needed (e.g., `Narrow()` at 50px for even more aggressive condensing), the pattern extends naturally: add another const and method. No need to design for this now.
