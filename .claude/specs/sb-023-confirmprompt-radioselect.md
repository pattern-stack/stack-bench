---
title: "SB-023: ConfirmPrompt + RadioSelect"
date: 2026-03-24
status: draft
branch:
depends_on:
  - SB-014
adrs: [ADR-001]
---

# SB-023: ConfirmPrompt + RadioSelect

## Goal

Build two interaction molecules for the Go CLI: ConfirmPrompt (binary yes/no choice for agent approvals) and RadioSelect (list selection with cursor for agent/conversation picking). Both are pure render functions following the established `(RenderContext, Data) -> string` pattern. State (selected index, cursor position) is managed by the caller. These compose existing atoms (TextBlock, Badge, Icon) and resolve all styling through the theme token system.

## File Tree

```
app/cli/internal/ui/components/molecules/        # NEW directory
  molecules.go                                    # Package declaration
  molecules_test.go                               # Shared test utilities (testContext helper)
  confirmprompt.go                                # ConfirmPrompt render function
  confirmprompt_test.go                           # ConfirmPrompt tests
  radioselect.go                                  # RadioSelect render function
  radioselect_test.go                             # RadioSelect tests
```

Note: The `molecules/` directory does not exist yet. SB-021 and SB-022 may create it first depending on execution order. If this issue lands first, it creates the directory and the `molecules.go` package file.

## Interfaces and Structs

### molecules.go -- Package declaration

```go
package molecules

// No shared types needed for this issue. The package file establishes
// the molecules package and its import of atoms.
```

### molecules_test.go -- Shared test helper

Mirrors the pattern in `atoms/atoms_test.go`:

```go
package molecules

import (
    "github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
    "github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

func testContext(t *theme.Theme, width int) atoms.RenderContext {
    return atoms.RenderContext{Width: width, Theme: t}
}
```

### confirmprompt.go -- ConfirmPrompt

```go
package molecules

import (
    "strings"

    "github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
    "github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// ConfirmPromptData carries the data for a binary choice prompt.
type ConfirmPromptData struct {
    Question string   // The question text to display
    Options  []string // e.g., ["Yes", "No"] or ["Approve", "Reject"]
    Selected int      // Index of currently selected option
}

// ConfirmPrompt renders a binary choice prompt.
// The question is rendered as a TextBlock, followed by the options as Badges.
// The selected option uses BadgeFilled variant; unselected options use BadgeOutline.
//
// Layout:
//   Question text
//   [Option1]  Option2    (when Selected=0)
//    Option1  [Option2]   (when Selected=1)
func ConfirmPrompt(ctx atoms.RenderContext, data ConfirmPromptData) string
```

**Composition details:**

1. Question line: `atoms.TextBlock` with `theme.Style{Hierarchy: theme.Secondary}` -- normal weight, default foreground. Uses a zero-width inner context so the text does not pad to full terminal width.
2. Options line: For each option, render an `atoms.Badge`:
   - Selected option: `BadgeFilled` variant with `theme.Style{Category: theme.CatAgent}` -- accent background, stands out.
   - Unselected options: `BadgeOutline` variant with `theme.Style{Hierarchy: theme.Tertiary}` -- dim, bracketed.
3. Options are joined with two spaces between them.
4. Question and options are joined with a newline.

### radioselect.go -- RadioSelect

```go
package molecules

import (
    "strings"

    "github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
    "github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// RadioItem represents a single selectable item in a RadioSelect list.
type RadioItem struct {
    Label       string // Primary text shown for this item
    Description string // Optional secondary text (shown dim)
}

// RadioSelectData carries the data for a list selection component.
type RadioSelectData struct {
    Label  string      // Optional header label above the list
    Items  []RadioItem // The selectable items
    Cursor int         // Index of the currently highlighted item
}

// RadioSelect renders a vertical list with a cursor indicator on the selected item.
// Each item shows an Icon (cursor or space), a label, and an optional description.
//
// Layout:
//   Label text (if non-empty)
//
//   > Item one       Description for item one
//     Item two       Description for item two
//     Item three     Description for item three
func RadioSelect(ctx atoms.RenderContext, data RadioSelectData) string
```

**Composition details:**

1. Label (if non-empty): `atoms.TextBlock` with `theme.Style{Hierarchy: theme.Primary, Emphasis: theme.Strong}` -- bold heading. Uses zero-width inner context.
2. For each item:
   - Cursor prefix: `atoms.Icon(ctx, atoms.IconCursor, theme.Style{Category: theme.CatAgent})` for the item at cursor position, or `"  "` (two spaces, matching glyph width) for others.
   - Label text: `atoms.TextBlock` with zero-width inner context:
     - Selected: `theme.Style{Category: theme.CatAgent, Hierarchy: theme.Secondary}` -- accent colored.
     - Unselected: `theme.Style{Hierarchy: theme.Secondary}` -- default foreground.
   - Description (if non-empty): `atoms.TextBlock` with `theme.Style{Hierarchy: theme.Tertiary}` -- dim supporting text, zero-width inner context.
3. Each item's parts are joined inline with a single space separator.
4. Items are joined with newlines.
5. If label was rendered, prepend it followed by `"\n\n"` before the items.

**Width handling:** Inner `atoms.TextBlock` calls use a zero-width `RenderContext` (copy ctx, set Width=0) so text spans are not padded. The molecule assembles inline spans into lines.

## Implementation Steps

### Step 1: Create the molecules directory and package file

Create `app/cli/internal/ui/components/molecules/molecules.go` with the package declaration. Create `molecules_test.go` with the `testContext` helper following the same pattern as `atoms/atoms_test.go`.

### Step 2: Implement ConfirmPrompt

Create `confirmprompt.go`:

1. Build a zero-width inner context: `innerCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}`.
2. Render the question text via `atoms.TextBlock(innerCtx, atoms.TextBlockData{Text: data.Question, Style: theme.Style{Hierarchy: theme.Secondary}})`.
3. Build the options line by iterating `data.Options`:
   - Clamp `data.Selected` to `[0, len(data.Options)-1]`.
   - For `i == selected`: `atoms.Badge(innerCtx, atoms.BadgeData{Label: opt, Style: theme.Style{Category: theme.CatAgent}, Variant: atoms.BadgeFilled})`.
   - For `i != selected`: `atoms.Badge(innerCtx, atoms.BadgeData{Label: opt, Style: theme.Style{Hierarchy: theme.Tertiary}, Variant: atoms.BadgeOutline})`.
4. Join badges with `"  "`.
5. Return `question + "\n" + optionsLine`. If `Options` is empty, return question only.

### Step 3: Test ConfirmPrompt

Create `confirmprompt_test.go`:

| Test | Assertion |
|------|-----------|
| `TestConfirmPromptRenders` | Non-empty output containing question text |
| `TestConfirmPromptContainsOptions` | Output contains all option label text |
| `TestConfirmPromptSelectedChangesOutput` | `Selected=0` vs `Selected=1` produce different output |
| `TestConfirmPromptEmptyOptions` | Returns question text only, no panic |
| `TestConfirmPromptDifferentThemes` | Dark vs light produce different ANSI output |
| `TestConfirmPromptNoNewlineInOptions` | Options line contains no embedded newlines |

### Step 4: Implement RadioSelect

Create `radioselect.go`:

1. Build a zero-width inner context.
2. Clamp `data.Cursor` to `[0, len(data.Items)-1]`.
3. If `data.Label` is non-empty, render via `atoms.TextBlock` with `{Hierarchy: Primary, Emphasis: Strong}`.
4. For each item at index `i`:
   - `prefix`: `atoms.Icon(innerCtx, atoms.IconCursor, theme.Style{Category: theme.CatAgent})` if `i == cursor`, else `"  "`.
   - `label`: `atoms.TextBlock(innerCtx, ...)` with accent style if selected, secondary style otherwise.
   - `desc`: if `item.Description != ""`, render `atoms.TextBlock(innerCtx, ...)` with tertiary style.
   - Join parts: `prefix + " " + label` (+ `"  " + desc` if present).
5. Join item lines with `"\n"`.
6. If label exists, return `label + "\n\n" + items`. Otherwise return items only.
7. If items is empty, return label only (or `""`).

### Step 5: Test RadioSelect

Create `radioselect_test.go`:

| Test | Assertion |
|------|-----------|
| `TestRadioSelectRenders` | Non-empty output for a 3-item list |
| `TestRadioSelectCursorGlyph` | Output contains `>` character |
| `TestRadioSelectContainsLabels` | Output contains all item labels |
| `TestRadioSelectContainsDescriptions` | Output contains description text |
| `TestRadioSelectCursorChangesOutput` | Different `Cursor` values produce different output |
| `TestRadioSelectWithLabel` | Output contains the header label |
| `TestRadioSelectWithoutLabel` | Empty label omits heading, first line is an item |
| `TestRadioSelectEmptyItems` | No panic, returns empty or label-only |
| `TestRadioSelectDifferentThemes` | Dark vs light produce different output |
| `TestRadioSelectLineCount` | Number of item-containing lines matches `len(Items)` |

### Step 6: Verify

```bash
cd /Users/dug/Projects/stack-bench/app/cli && go test ./internal/ui/components/molecules/...
```

All tests pass. No changes to existing files.

## Testing Strategy

All tests follow the patterns established in `atoms/*_test.go`:

1. **Test helper**: `testContext(t *theme.Theme, width int) atoms.RenderContext` in `molecules_test.go`, matching the atoms pattern.
2. **Theme injection**: Every test creates an explicit `RenderContext` with `theme.DarkTheme()` -- no global state dependency.
3. **Theme variation tests**: At least one test per component swaps dark/light themes and asserts different output.
4. **String content assertions**: Tests use `strings.Contains` to check for expected text content (labels, descriptions, glyphs). Avoids brittle ANSI-sequence matching while validating composition.
5. **Structural assertions**: Tests verify that changing state (Selected/Cursor index) changes output.
6. **Edge cases**: Empty slices, out-of-range indices, empty strings tested to prevent panics.

No snapshot/golden-file tests for v1. Inline `strings.Contains` assertions are sufficient and match the atom test precedent.

## Atom Composition Summary

| Molecule | Atoms Used | How |
|----------|-----------|-----|
| ConfirmPrompt | `TextBlock` | Renders the question text |
| ConfirmPrompt | `Badge` (Filled + Outline) | Renders each option; filled for selected, outline for unselected |
| RadioSelect | `TextBlock` | Renders the header label, item labels, and item descriptions |
| RadioSelect | `Icon` (`IconCursor`) | Renders the `>` cursor glyph on the selected item |

Both molecules use `atoms.RenderContext` for theme access and resolve all styling through `theme.Style` tokens. Neither molecule constructs a `lipgloss.Style` directly.

## Open Questions

None. The data structures and rendering approach are defined in the parent spec (2026-03-21-cli-component-system.md, Molecule Specifications section). This spec fills in the composition details, styling choices, and edge case handling.
