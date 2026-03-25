---
title: "SB-022: ToolCallBlock + DiffBlock"
date: 2026-03-24
status: draft
branch:
depends_on:
  - SB-021
adrs: [ADR-001]
---

# SB-022: ToolCallBlock + DiffBlock

## Goal

Build two molecule components for the Go CLI: ToolCallBlock (tool invocation display with status and collapsible I/O) and DiffBlock (colored unified diff renderer). Both are pure render functions following `(RenderContext, Data) -> string`.

## File Tree

```
app/cli/internal/ui/components/molecules/
  toolcallblock.go       # ToolCallBlock render function + ToolStatus enum
  toolcallblock_test.go  # ToolCallBlock tests
  diffblock.go           # DiffBlock render function + DiffLineType enum
  diffblock_test.go      # DiffBlock tests
```

## Types and Interfaces

### ToolCallBlock

```go
package molecules

type ToolStatus int

const (
    ToolRunning ToolStatus = iota
    ToolSuccess
    ToolError
)

type ToolCallData struct {
    Name      string     // tool name, e.g. "edit_file"
    Status    ToolStatus // Running, Success, Error
    Input     string     // tool input/arguments (shown in collapsed CodeBlock)
    Output    string     // tool output/result (shown in collapsed CodeBlock)
    Error     string     // error message (shown when Status == ToolError)
    Collapsed bool       // if true, hide input/output CodeBlocks
}

// ToolCallBlock renders a tool invocation display.
// Header: Icon(status) + Badge(tool name, filled, CatTool) + Badge(status label, outline, status color)
// Body (when not collapsed): CodeBlock(input) + CodeBlock(output) or error text
func ToolCallBlock(ctx atoms.RenderContext, data ToolCallData) string
```

**Composition:**
1. Header line:
   - Status icon: `atoms.Icon` — `IconDot` for Running (theme.Running), `IconCheck` for Success (theme.Success), `IconX` for Error (theme.Error)
   - Tool name: `atoms.Badge` — `BadgeFilled` with `theme.Style{Category: theme.CatTool}`
   - Status label: `atoms.Badge` — `BadgeOutline` with status-mapped `theme.Style{Status: ...}`
     - Running: "running", Success: "done", Error: "failed"
2. Body (when `!Collapsed`):
   - If `Status == ToolError && Error != ""`: error text with `theme.Style{Status: theme.Error}`
   - If `Input != ""`: `atoms.CodeBlock` with input
   - If `Output != ""`: `atoms.CodeBlock` with output
3. Parts joined with newlines.

### DiffBlock

```go
type DiffLineType int

const (
    DiffContext DiffLineType = iota
    DiffAdded
    DiffRemoved
)

type DiffLine struct {
    Type    DiffLineType
    Content string
}

type DiffBlockData struct {
    Filename string     // displayed as a Badge header
    Lines    []DiffLine // the diff content
}

// DiffBlock renders a colored unified diff.
// Header: Badge(filename, filled)
// Body: per-line colored output with gutter markers
func DiffBlock(ctx atoms.RenderContext, data DiffBlockData) string
```

**Composition:**
1. Header: `atoms.Badge` with filename, `BadgeFilled`, `theme.Style{Hierarchy: theme.Secondary}`
2. Per-line rendering (zero-width inner context):
   - `DiffAdded`: `+` prefix, `theme.Style{Status: theme.Success}` (green)
   - `DiffRemoved`: `-` prefix, `theme.Style{Status: theme.Error}` (red)
   - `DiffContext`: ` ` prefix, `theme.Style{Hierarchy: theme.Tertiary}` (dim)
3. Lines joined with newlines, header + blank line + body.

### ParseUnifiedDiff helper

```go
// ParseUnifiedDiff converts a unified diff string into []DiffLine.
// Lines starting with '+' (not '+++') are Added, '-' (not '---') are Removed, else Context.
func ParseUnifiedDiff(diff string) []DiffLine
```

## Implementation Steps

### Step 1: ToolCallBlock + tests
1. Create `toolcallblock.go` with ToolStatus enum and ToolCallBlock function
2. Create `toolcallblock_test.go`:
   - TestToolCallBlockRunning — renders name + "running" status
   - TestToolCallBlockSuccess — renders name + "done" status
   - TestToolCallBlockError — renders name + "failed" + error text
   - TestToolCallBlockCollapsed — hides input/output when collapsed
   - TestToolCallBlockExpanded — shows input/output CodeBlocks
   - TestToolCallBlockDifferentThemes — dark vs light differ

### Step 2: DiffBlock + tests
1. Create `diffblock.go` with DiffLineType, DiffLine, DiffBlockData, DiffBlock, ParseUnifiedDiff
2. Create `diffblock_test.go`:
   - TestDiffBlockRendersFilename — output contains filename
   - TestDiffBlockAddedLines — added lines colored (contain content)
   - TestDiffBlockRemovedLines — removed lines colored
   - TestDiffBlockContextLines — context lines dim
   - TestDiffBlockMixedLines — all three types render
   - TestDiffBlockParseUnifiedDiff — parses +/- lines correctly
   - TestDiffBlockDifferentThemes — dark vs light differ
   - TestDiffBlockEmptyLines — no panic on empty input

### Step 3: Verify
```bash
cd /Users/dug/Projects/stack-bench/app/cli
go test ./internal/ui/components/molecules/...
go vet ./internal/ui/components/...
```

## Testing Strategy

All tests follow the molecules test pattern:
- `testContext(theme, width)` helper
- `theme.DarkTheme()` / `theme.LightTheme()` for theme variation
- `strings.Contains` assertions
- Edge cases: empty input/output, collapsed state, empty diff
