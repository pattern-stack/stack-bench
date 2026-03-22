---
title: CLI Component System
date: 2026-03-21
status: draft
branch: dugshub/cli-components/1-component-system
depends_on: []
adrs: [ADR-001]
---

# CLI Component System

## Goal

Introduce an atoms-and-molecules component layer to the Go/Bubble Tea CLI so that every piece of rendered UI is a composable, token-driven, theme-aware building block. This replaces the current pattern of inlining `ui.Bold`, `ui.Dim`, `ui.Accent` calls throughout views with structured components that declare semantic intent via `theme.Style` tokens. The component inventory is designed for 1:1 parity with a future React frontend: same names, same semantics, different renderers.

## Domain Model

### Rendering Pipeline

```
Data + Width --> Component(theme.Style tokens) --> theme.Resolve() --> lipgloss.Style --> string
```

Every component is a **pure render function**: it takes typed data plus a terminal width, resolves its styling through the active theme's token system, and returns a string. Components are NOT Bubble Tea models. The only exceptions are molecules that require internal state (Spinner, AutocompleteDropdown) -- these wrap a minimal `tea.Model` internally but still expose a `View() string` surface.

### Token System (existing, unchanged)

The four token dimensions from `cli/internal/ui/theme/tokens.go` are the sole styling vocabulary:

| Dimension | Values | Purpose |
|-----------|--------|---------|
| Category | CatAgent, CatSystem, CatTool, CatUser, Cat5-8 | Semantic color domain |
| Hierarchy | Primary, Secondary, Tertiary, Quaternary | Visual importance |
| Emphasis | Strong, Normal, Subtle | Text weight |
| Status | NoStatus, Success, Error, Warning, Info, Muted, Running | Operational state |

Components declare a `theme.Style` struct combining these dimensions. The theme's `Resolve(Style) lipgloss.Style` maps intent to appearance. No component ever constructs a `lipgloss.Style` directly.

### DisplayStyle: The Component-Level Token Contract

Each atom declares which token combination it needs via a `DisplayStyle` -- a named alias for a `theme.Style` that carries semantic meaning at the component level. This is the bridge between "what the component wants to express" and "what the theme renders."

```
DisplayStyle = theme.Style (same struct, used as a parameter name to signal intent)
```

For example, a Badge rendering a role label uses `{Category: CatAgent, Hierarchy: Secondary, Emphasis: Normal, Status: NoStatus}`. A Badge rendering an error status uses `{Status: Error, Emphasis: Strong}`. The component does not know what colors these produce -- the theme decides.

## Package Structure

```
app/cli/internal/ui/
  components/
    atoms/
      atoms.go          -- Package declaration, shared types (Role, DisplayStyle alias, RenderContext)
      textblock.go      -- TextBlock: styled text span
      codeblock.go      -- CodeBlock: syntax-highlighted code with language label, line numbers
      inlinecode.go     -- InlineCode: monospace span for inline use
      separator.go      -- Separator: horizontal rule (full-width dim line)
      spinner.go        -- Spinner: animated braille indicator (wraps tea.Model)
      badge.go          -- Badge: small label (role, status, language, file type)
      icon.go           -- Icon: semantic glyphs (cursor, arrow, bullet, check, x)
    molecules/
      molecules.go      -- Package declaration, shared molecule types
      messageblock.go   -- MessageBlock: Badge(role) + rendered content
      statusblock.go    -- StatusBlock: Spinner + TextBlock(verb) + optional Badge
      toolcallblock.go  -- ToolCallBlock: Badge(tool) + Badge(status) + collapsible CodeBlock
      diffblock.go      -- DiffBlock: Badge(filename) + colored diff lines
      errorblock.go     -- ErrorBlock: Badge(error) + TextBlock + optional suggestions
      header.go         -- Header: TextBlock(title) + Badge(s) + Separator
      statusbar.go      -- StatusBar: Separator + TextBlock(hints) + Badge(health)
      confirmprompt.go  -- ConfirmPrompt: TextBlock(question) + Badge(options)
      radioselect.go    -- RadioSelect: TextBlock(label) + list with Icon(cursor)
      autocomplete.go   -- AutocompleteDropdown: list with Badge(type) (wraps tea.Model)
  theme/                -- (existing, unchanged)
    tokens.go
    theme.go
    themes.go
    registry.go
  markdown.go           -- (existing, refactored in Phase 3 to use atoms)
  styles.go             -- (existing, deprecated in Phase 5)
```

### Why atoms/ and molecules/ subdirectories

Flat structure was considered. Two subdirectories are better because:
1. Import paths signal intent: `atoms.TextBlock` vs `molecules.MessageBlock` -- the caller knows the abstraction level.
2. Dependency direction is enforced by Go's package system: `molecules` imports `atoms`, but `atoms` never imports `molecules`. A flat package cannot enforce this.
3. The naming mirrors the React frontend structure (`components/atoms/`, `components/molecules/`) for parity.

## Shared Types

### Role

The `Role` type is shared between the `chat` package and the component system. To avoid duplication, it lives in `atoms/` and is imported by both:

```go
// atoms/atoms.go
type Role int
const (
    RoleUser Role = iota
    RoleAssistant
    RoleSystem
)
```

The existing `chat.Role` type will be replaced with `atoms.Role` during the Phase 3 migration.

## Atom Specifications

### RenderContext (shared)

Every render function receives a `RenderContext` instead of passing width, theme, etc. as individual parameters. This keeps signatures stable as we add capabilities (e.g., color mode, indentation level). Using RenderContext also enables test isolation -- tests inject a specific theme without touching global state.

```go
// atoms/atoms.go
type RenderContext struct {
    Width int
    Theme *theme.Theme
}

func DefaultContext(width int) RenderContext {
    return RenderContext{Width: width, Theme: theme.Active()}
}
```

### TextBlock

Renders a string with a resolved `theme.Style`. The fundamental atom -- most other components delegate to TextBlock for their text portions.

```go
// atoms/textblock.go
type TextBlockData struct {
    Text  string
    Style theme.Style
}

func TextBlock(ctx RenderContext, data TextBlockData) string
```

### CodeBlock

Renders a multi-line code block with optional language label and line numbers. Uses a left-border gutter for visual distinction.

```go
// atoms/codeblock.go
type CodeBlockData struct {
    Code        string
    Language    string // displayed as a dim label above the block
    LineNumbers bool
}

func CodeBlock(ctx RenderContext, data CodeBlockData) string
```

Styling: code text uses `{Category: CatTool, Hierarchy: Secondary}`. Language label uses `{Hierarchy: Tertiary}`. Line numbers use `{Hierarchy: Quaternary}`. Gutter border uses `{Hierarchy: Tertiary}` (Tertiary overrides Category to DimColor).

### InlineCode

Renders a short code span within flowing text. Differs from CodeBlock in that it produces no newlines and is meant to be embedded in a TextBlock line.

```go
// atoms/inlinecode.go
func InlineCode(ctx RenderContext, code string) string
```

Styling: `{Status: Success, Hierarchy: Secondary}`. The Secondary hierarchy prevents the Primary default from triggering Bold, matching the current non-bold green rendering in `markdown.go`.

### Separator

Renders a full-width horizontal rule using box-drawing characters.

```go
// atoms/separator.go
func Separator(ctx RenderContext) string
```

Styling: `{Hierarchy: Tertiary}`. Note: Tertiary hierarchy resolves to `DimColor` which overrides any Category value, so no Category is specified.

### Spinner

The one atom that wraps a `tea.Model` because it requires animation state (frame index, tick timing). Exposes `Update` and `View` but is otherwise a pure rendering concern.

```go
// atoms/spinner.go
type SpinnerModel struct { /* tick state, frame index */ }

func NewSpinner() SpinnerModel
func (s SpinnerModel) Update(msg tea.Msg) (SpinnerModel, tea.Cmd)
func (s SpinnerModel) Init() tea.Cmd
func (s SpinnerModel) View() string
```

Uses braille character animation. Styling: `{Category: CatAgent, Status: Running}`.

### Badge

Small inline label. Used for role indicators, status tags, language labels, file types. Has two visual modes: `Filled` (background color) and `Outline` (text color only, brackets).

```go
// atoms/badge.go
type BadgeVariant int
const (
    BadgeFilled BadgeVariant = iota
    BadgeOutline
)

type BadgeData struct {
    Label    string
    Style    theme.Style
    Variant  BadgeVariant
    MaxWidth int // 0 = default (16 chars), truncates with ellipsis
}

func Badge(ctx RenderContext, data BadgeData) string
```

Filled variant renders with `lipgloss.Background` set from the resolved color. Outline variant renders as `[label]` with foreground color. Default max width is 16 characters with ellipsis.

### Icon

Semantic glyph lookup. Maps logical names to Unicode characters. Pure function, no state.

```go
// atoms/icon.go
type IconName int
const (
    IconCursor  IconName = iota // >
    IconArrow                   // ->
    IconBullet                  // *
    IconCheck                   // checkmark
    IconX                       // x mark
    IconDot                     // filled circle
    IconCircle                  // empty circle
    IconWarning                 // triangle
    IconInfo                    // i
)

func Icon(ctx RenderContext, name IconName, style theme.Style) string
```

## Molecule Specifications

Molecules compose atoms. They import the `atoms` package and never construct `lipgloss.Style` directly.

### MessageBlock

The primary molecule for the chat view. Replaces the current `renderMessage` function in `chat/view.go`.

```go
// molecules/messageblock.go
type MessageBlockData struct {
    Role    atoms.Role
    Content string // raw markdown for assistant, plain text for user/system
}

func MessageBlock(ctx atoms.RenderContext, data MessageBlockData) string
```

Internally: `Badge(role label)` + content rendered through the markdown pipeline (which itself uses TextBlock, CodeBlock, InlineCode atoms). Role determines the Badge style:
- User: `{Category: CatUser, Emphasis: Subtle}` outline badge
- Assistant: `{Category: CatAgent}` filled badge
- System: `{Category: CatSystem}` outline badge

### StatusBlock

Renders an ongoing operation: thinking indicator, tool progress, any async status. Replaces the current `ui.Accent.Render("  ...")` streaming indicator.

```go
// molecules/statusblock.go
type StatusBlockData struct {
    Verb    string       // "Thinking", "Reading file", "Running tests"
    Detail  string       // optional secondary text
    Elapsed *time.Duration // optional timer
    Count   *int         // optional counter (e.g., "3 files")
}

func StatusBlock(ctx atoms.RenderContext, spinner atoms.SpinnerModel, data StatusBlockData) string
```

Internally: `Spinner` + `TextBlock(verb, {Category: CatAgent, Status: Running})` + optional `Badge(elapsed)` + optional `Badge(count)`.

### ToolCallBlock

Renders a tool invocation with its status and collapsible input/output. Not yet needed for MVP but designed here for completeness.

```go
// molecules/toolcallblock.go
type ToolStatus int
const (
    ToolRunning ToolStatus = iota
    ToolSuccess
    ToolError
)

type ToolCallBlockData struct {
    ToolName string
    Status   ToolStatus
    Input    string // JSON or text, rendered as CodeBlock when expanded
    Output   string // rendered as CodeBlock when expanded
    Expanded bool
}

func ToolCallBlock(ctx atoms.RenderContext, data ToolCallBlockData) string
```

### ErrorBlock

Structured error display with optional recovery suggestions.

```go
// molecules/errorblock.go
type ErrorBlockData struct {
    Title       string
    Message     string
    Suggestions []string // optional "try this" hints
}

func ErrorBlock(ctx atoms.RenderContext, data ErrorBlockData) string
```

Internally: `Badge("error", {Status: Error})` + `TextBlock(message)` + optional `TextBlock(suggestions, {Hierarchy: Tertiary})`.

### Header

Top-of-view header bar. Replaces `renderHeader` in `chat/view.go`.

```go
// molecules/header.go
type HeaderData struct {
    Title  string
    Badges []atoms.BadgeData
}

func Header(ctx atoms.RenderContext, data HeaderData) string
```

Internally: `TextBlock(title, {Hierarchy: Primary, Emphasis: Strong})` + `Badge` list + `Separator`.

### StatusBar

Bottom-of-view status bar. Replaces `renderStatus` in `app/model.go`.

```go
// molecules/statusbar.go
type HealthState int
const (
    HealthUnknown HealthState = iota
    HealthStarting
    HealthHealthy
    HealthUnhealthy
)

type StatusBarData struct {
    Hints       string
    ServiceName string
    Health      HealthState
}

func StatusBar(ctx atoms.RenderContext, data StatusBarData) string
```

Internally: `Separator` + `TextBlock(hints, {Hierarchy: Tertiary})` + `Icon(dot)` + `TextBlock(service, {Hierarchy: Tertiary})`.

Note: The `HealthState` enum maps directly from the existing `service.ServiceStatus` type. The StatusBar accepts `HealthState` to avoid importing the `service` package -- the caller (app/model.go) converts between them.

### RadioSelect

List selection with cursor. Replaces the inline agent selector in `app/model.go` `viewAgentSelect`.

```go
// molecules/radioselect.go
type RadioItem struct {
    Label       string
    Description string
}

type RadioSelectData struct {
    Items  []RadioItem
    Cursor int
}

func RadioSelect(ctx atoms.RenderContext, data RadioSelectData) string
```

Internally: for each item, `Icon(IconCursor)` (on selected) + `TextBlock(label)` + `TextBlock(description, {Hierarchy: Tertiary})`.

### ConfirmPrompt

Binary choice prompt. Not needed for MVP but included for inventory completeness.

```go
// molecules/confirmprompt.go
type ConfirmPromptData struct {
    Question string
    Options  []string // e.g., ["Yes", "No"]
    Selected int
}

func ConfirmPrompt(ctx atoms.RenderContext, data ConfirmPromptData) string
```

### AutocompleteDropdown

Wraps a `tea.Model` for state (cursor position, filter). Replaces the existing `ui/autocomplete/autocomplete.go` with a component-system-native implementation.

```go
// molecules/autocomplete.go
// This molecule wraps state. Its View() uses atoms internally.
// The existing autocomplete.Model is migrated here in Phase 6.
```

### DiffBlock

File diff display. Not needed for MVP. Planned for when tool call output includes diffs.

```go
// molecules/diffblock.go
type DiffLine struct {
    Type    DiffLineType // Added, Removed, Context
    Content string
}

type DiffBlockData struct {
    Filename string
    Lines    []DiffLine
}

func DiffBlock(ctx atoms.RenderContext, data DiffBlockData) string
```

## Markdown Renderer Token Mappings

The existing `RenderMarkdown` function in `ui/markdown.go` has internal styles for heading levels, bold, italic, links, and list bullets. When refactored in Phase 3 to use atoms, these will map to token combinations passed to `TextBlock`:

| Markdown Element | Token Mapping | Notes |
|---|---|---|
| H1 | `{Category: CatAgent, Hierarchy: Primary, Emphasis: Strong}` | Bold, accent colored |
| H2 | `{Category: CatSystem, Hierarchy: Primary, Emphasis: Strong}` | Bold, system colored |
| H3 | `{Hierarchy: Primary, Emphasis: Strong}` | Bold, default foreground |
| Bold | `{Emphasis: Strong}` | Applied within TextBlock |
| Italic | Rendered via lipgloss Italic directly | No token dimension for italic; applied as a modifier |
| Link | `{Category: CatAgent, Hierarchy: Secondary}` | Underline applied as modifier |
| List bullet | `{Category: CatAgent}` | Bullet glyph via Icon atom |
| Inline code | `{Status: Success, Hierarchy: Secondary}` | Delegates to InlineCode atom |
| Code fence | Delegates to CodeBlock atom | Full atom delegation |

These are not separate atoms -- they are inline formatting applied within TextBlock renders. The `RenderMarkdown` function continues to own this mapping but uses atoms for the actual rendering.

## Implementation Phases

| Phase | What | Depends On | Scope |
|-------|------|------------|-------|
| 1 | Core atoms | -- | TextBlock, CodeBlock, InlineCode, Separator, Badge, Icon (Tree deferred to Phase 6) |
| 2 | Chat molecules | Phase 1 | MessageBlock, Header, StatusBar, ErrorBlock |
| 3 | Chat view migration | Phase 2 | Refactor chat/view.go and app/model.go to use molecules |
| 4 | Stateful components | Phase 1 | Spinner, StatusBlock, RadioSelect |
| 5 | Deprecate ui/styles.go | Phase 3 | Remove Dim/Fg/Bold/Green/Red/Accent convenience vars |
| 6 | Remaining molecules + Tree | Phase 4 | ToolCallBlock, DiffBlock, ConfirmPrompt, AutocompleteDropdown migration, Tree atom |

### Phase 1: Core Atoms

Create `app/cli/internal/ui/components/atoms/` with:
- `atoms.go` -- RenderContext, Role, DisplayStyle alias
- `textblock.go` -- TextBlock function
- `codeblock.go` -- CodeBlock function (absorb logic from `ui/markdown.go` `renderCodeBlock`)
- `inlinecode.go` -- InlineCode function (absorb logic from `ui/markdown.go` `mdCode` usage)
- `separator.go` -- Separator function
- `badge.go` -- Badge function with Filled/Outline variants
- `icon.go` -- Icon function with glyph registry

Note: `tree.go` (Tree atom) is deferred to Phase 6 as no current view or molecule requires it.

Testing: unit tests for each atom. Test that output changes when theme changes (swap dark/light, assert different ANSI sequences). Test width truncation behavior.

### Phase 2: Chat Molecules

Create `app/cli/internal/ui/components/molecules/` with:
- `molecules.go` -- shared types
- `messageblock.go` -- replaces `renderMessage` in chat/view.go
- `header.go` -- replaces `renderHeader` in chat/view.go
- `statusbar.go` -- replaces `renderStatus` in app/model.go
- `errorblock.go` -- structured error display

Testing: snapshot tests comparing molecule output against expected strings for known inputs. Test that MessageBlock correctly delegates to Badge + markdown rendering.

### Phase 3: Chat View Migration

Refactor existing views to call molecules instead of inline styling:
- `chat/view.go` `renderMessage` -> `molecules.MessageBlock`
- `chat/view.go` `renderHeader` -> `molecules.Header`
- `chat/view.go` `renderPrompt` -> `molecules.Prompt`
- `app/model.go` `renderStatus` -> `molecules.StatusBar`
- `app/model.go` `viewAgentSelect` -> uses `molecules.RadioSelect` + `molecules.Header`
- `chat/picker.go` `View` -> uses `molecules.Header` + `molecules.RadioSelect`

Refactor `ui/markdown.go` `RenderMarkdown` to use `atoms.TextBlock`, `atoms.CodeBlock`, `atoms.InlineCode` internally. The function signature stays the same for backward compatibility during migration, but internals switch to atoms.

### Phase 4: Stateful Components

- `atoms/spinner.go` -- Spinner with tea.Model
- `molecules/statusblock.go` -- StatusBlock using Spinner (replaces `ui.Accent.Render("  ...")`)
- `molecules/radioselect.go` -- RadioSelect (pure render, state managed by caller)

Requires wiring Spinner's `Update`/`Init` into the parent Bubble Tea model's message loop.

### Phase 5: Deprecate ui/styles.go

Remove the convenience vars (`ui.Dim`, `ui.Fg`, `ui.Bold`, `ui.Green`, `ui.Red`, `ui.Accent`) and `RefreshStyles()`. All callers will have been migrated to use components or direct `theme.Resolve()` calls in Phases 3-4.

### Phase 6: Remaining Molecules + Tree

Build out the full inventory for tool call display, diffs, confirmation prompts, Tree atom, and migrate the existing autocomplete widget. These are needed as the CLI gains richer agent interaction (tool use visibility, file editing confirmation).

## Key Design Decisions

### Pure functions over Bubble Tea models

Components are functions `(RenderContext, Data) -> string`, not `tea.Model` implementations. Rationale:
1. Most UI rendering is stateless -- given the same data, produce the same output.
2. State management belongs in the view layer (chat/Model, app/Model), not in display components.
3. Pure functions are trivially testable without Bubble Tea's message loop.
4. Only Spinner and AutocompleteDropdown need state, and they are explicitly called out as exceptions.

### RenderContext over individual parameters

Passing `(width, theme)` as a struct instead of individual args keeps every function signature at exactly two parameters: context + data. When we later add capabilities (color mode detection, nesting depth for indentation, right-to-left support), we extend RenderContext without touching any function signatures.

### Separate atoms/ and molecules/ packages

Go's package system enforces the dependency rule: molecules import atoms, atoms never import molecules. A single flat package would rely on developer discipline to maintain this boundary. The two-package split makes the architecture self-enforcing.

### No new token types

The existing `theme.Style` with its four dimensions (Category, Hierarchy, Emphasis, Status) is sufficient for all planned components. Components just need to choose the right combination. Adding new token types would mean changing the theme system, which is stable and shared with the future frontend.

### Markdown renderer becomes an atom consumer

The existing `RenderMarkdown` function in `ui/markdown.go` currently constructs `lipgloss.Style` directly (e.g., `mdH1`, `mdCode`). In Phase 3, it will be refactored to call `atoms.TextBlock`, `atoms.CodeBlock`, and `atoms.InlineCode` internally. This means markdown rendering automatically benefits from theme changes and maintains consistency with the rest of the component system. The public API (`RenderMarkdown(text, width) string`) does not change.

### Migration is incremental, not big-bang

Each phase produces a working CLI. Phase 1-2 create the new components alongside the old code. Phase 3 swaps call sites one at a time. Phase 5 removes the old code only after all callers are migrated. At no point is the CLI broken.

## Frontend Parity

The component names and data contracts are designed to map directly to React components:

| CLI (Go) | Frontend (React) | Shared Semantics |
|----------|-----------------|------------------|
| `atoms.TextBlock(ctx, {Text, Style})` | `<TextBlock style={style}>{text}</TextBlock>` | Same style tokens, different renderers |
| `atoms.Badge(ctx, {Label, Style, Variant})` | `<Badge variant={variant} style={style}>{label}</Badge>` | Same variants (filled/outline) |
| `molecules.MessageBlock(ctx, {Role, Content})` | `<MessageBlock role={role}>{content}</MessageBlock>` | Same role enum, same composition |
| `molecules.StatusBar(ctx, {Hints, Health})` | `<StatusBar hints={hints} health={health} />` | Same health states |

The token system (`theme.Style`) is the shared design language. The CLI resolves tokens via `theme.Resolve() -> lipgloss.Style`. The frontend resolves the same token struct via a CSS-in-JS theme provider. Same intent, platform-native output.

## Testing Strategy

### Atom tests (unit)
- Each atom gets a `_test.go` file in `atoms/`.
- Test with both `DarkTheme()` and `LightTheme()` to verify token resolution produces different output.
- Test width constraints: TextBlock truncation, CodeBlock wrapping, Separator width.
- Test Badge variants (Filled vs Outline produce structurally different output).
- Test Icon returns correct glyphs for each IconName.

### Molecule tests (integration)
- Each molecule gets a `_test.go` file in `molecules/`.
- Test composition: MessageBlock output contains a Badge and styled content.
- Test role-specific rendering: user vs assistant vs system messages differ.
- Snapshot-style tests: known input -> expected output string (golden files optional, inline expected strings acceptable for v1).

### View migration tests (regression)
- Before migrating each view function, capture its current output for representative inputs.
- After migration, assert the new component-based output is visually equivalent (exact string match or semantic equivalence).

### No Bubble Tea test harness needed
- Since components are pure functions (except Spinner), they can be tested with standard `go test`.
- Spinner is tested by advancing its frame index and asserting View() output.

## Open Questions

1. **Should RenderMarkdown move into molecules?** Current decision: keep it in `ui/` but refactor internals to use atoms. The markdown token mapping table above documents how its internal styles map to token combinations.

2. **Collapsible sections for ToolCallBlock.** Defer to Phase 6 when ToolCallBlock is implemented. Options: (a) collapsed with key hint to expand, state in parent model; (b) fixed line count with "..." truncation.

3. **Badge width limits.** Proposal: Badge truncates at 16 characters with ellipsis by default, with an optional `MaxWidth` field on `BadgeData` to override per-instance.
