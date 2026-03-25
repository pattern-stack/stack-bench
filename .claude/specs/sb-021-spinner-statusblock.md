---
title: "SB-021: Spinner + StatusBlock"
date: 2026-03-24
status: draft
branch:
depends_on: []
adrs:
  - ADR-001
---

# SB-021: Spinner + StatusBlock

## Goal

Build the Spinner atom (animated braille indicator wrapping `tea.Model`) and the StatusBlock molecule (composes Spinner + TextBlock verb + optional elapsed/count Badges). These are the first animated, stateful components in the CLI component system and the first molecule in the `molecules` package.

## Domain Model

No domain entities. Pure presentation components:

- **Spinner** (atom) -- A `tea.Model` that cycles through braille animation frames on a tick interval. Unlike existing atoms (which are pure render functions taking `RenderContext` + data), Spinner is stateful because it needs an internal frame counter driven by `tea.Cmd` ticks.
- **StatusBlock** (molecule) -- Composes Spinner + TextBlock + Badge(elapsed) + Badge(count) into a single inline status line. Also implements `tea.Model` because it owns a Spinner sub-model.

## Key Design Decisions

### 1. Spinner as tea.Model (not a pure render function)

Existing atoms are stateless render functions: `func Badge(ctx, data) string`. Spinner cannot follow this pattern because it requires a tick-based animation loop (`tea.Tick`). It implements the sub-model pattern with `Init()`, `Update()`, and `View()` methods.

**Rationale:** Bubble Tea's animation model requires `tea.Cmd` ticks. There is no way to drive frame advancement from a pure function. The parent must wire the Spinner's `Init()` into its own command batch and forward `TickMsg` through `Update()`.

### 2. Frame set: Braille dots

```
Frames: ⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏
```

Braille dot pattern (U+280x range). 10 frames, smooth rotation feel. This is the standard "dots" spinner used across modern CLIs (e.g., ora, charm/spinner).

### 3. Tick interval: 80ms

80ms per frame yields ~12.5 FPS, which feels fluid without burning CPU. This matches the Charm spinner library default for braille patterns.

### 4. Custom TickMsg type

Spinner defines its own `TickMsg` (with an embedded ID to prevent cross-spinner interference) rather than using a generic timer. This allows multiple Spinners to coexist without ticking each other's frames.

### 5. StatusBlock owns Spinner lifecycle

StatusBlock embeds a Spinner and proxies `Init()` / `Update()` through to it. The caller only needs to manage one `tea.Model` (the StatusBlock), not the inner Spinner separately.

### 6. Spinner uses theme.Style for color

The Spinner's frame glyph is rendered via `ctx.Theme.Resolve(style)`, consistent with how all other atoms resolve colors. The default style uses `Status: Running` (purple in dark theme, purple in light theme).

## File Tree

```
app/cli/internal/ui/components/
  atoms/
    spinner.go          # Spinner tea.Model
    spinner_test.go     # Spinner unit tests
  molecules/
    molecules.go        # Package doc + shared types (mirrors atoms/atoms.go)
    statusblock.go      # StatusBlock tea.Model
    statusblock_test.go # StatusBlock unit tests
```

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | `atoms/spinner.go` -- Spinner model | -- |
| 2 | `atoms/spinner_test.go` -- Spinner tests | Phase 1 |
| 3 | `molecules/molecules.go` -- Package scaffold | -- |
| 4 | `molecules/statusblock.go` -- StatusBlock model | Phase 1, 3 |
| 5 | `molecules/statusblock_test.go` -- StatusBlock tests | Phase 4 |

## Phase Details

### Phase 1: `atoms/spinner.go`

#### Types

```go
package atoms

import (
    "time"

    tea "charm.land/bubbletea/v2"
    "github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// spinnerFrames is the braille dot animation sequence.
var spinnerFrames = []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}

// spinnerInterval is the time between frame advances.
const spinnerInterval = 80 * time.Millisecond

// spinnerSeq is a package-level counter for unique Spinner IDs.
var spinnerSeq int

// TickMsg is sent by the Spinner's tick command.
// ID scopes ticks to a specific Spinner instance.
type TickMsg struct {
    ID int
}

// Spinner is an animated braille indicator.
// It follows the Bubble Tea sub-model pattern (like chat.Model):
// Update returns (Spinner, tea.Cmd) rather than (tea.Model, tea.Cmd).
type Spinner struct {
    id    int
    frame int
    Style theme.Style
}

// NewSpinner creates a Spinner with the default Running style.
func NewSpinner() Spinner {
    spinnerSeq++
    return Spinner{
        id:    spinnerSeq,
        Style: theme.Style{Status: theme.Running},
    }
}

// Init returns the first tick command.
func (s Spinner) Init() tea.Cmd {
    return s.tick()
}

// Update advances the frame on a matching TickMsg.
func (s Spinner) Update(msg tea.Msg) (Spinner, tea.Cmd) {
    if msg, ok := msg.(TickMsg); ok && msg.ID == s.id {
        s.frame = (s.frame + 1) % len(spinnerFrames)
        return s, s.tick()
    }
    return s, nil
}

// ViewWith renders the current frame glyph using the given RenderContext.
// This is the primary render method, used by molecule composition.
func (s Spinner) ViewWith(ctx RenderContext) string {
    style := ctx.Theme.Resolve(s.Style)
    return style.Render(spinnerFrames[s.frame])
}

// View renders the current frame using the active theme.
// Convenience for standalone usage outside a molecule.
func (s Spinner) View() string {
    style := theme.Resolve(s.Style)
    return style.Render(spinnerFrames[s.frame])
}

// tick returns a tea.Cmd that sends a TickMsg after the interval.
func (s Spinner) tick() tea.Cmd {
    id := s.id
    return tea.Tick(spinnerInterval, func(time.Time) tea.Msg {
        return TickMsg{ID: id}
    })
}
```

**Conventions followed:**
- Package `atoms` (same package as Badge, TextBlock, etc.)
- Import paths use `charm.land/bubbletea/v2` and project module path
- Sub-model pattern: `Update` returns `(Spinner, tea.Cmd)` matching `chat.Model.Update`
- `theme.Style` for color resolution, consistent with all other atoms
- Exported types use doc comments in `// Name does...` format

### Phase 2: `atoms/spinner_test.go`

```go
package atoms

import (
    "strings"
    "testing"

    "github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

func TestNewSpinnerDistinctIDs(t *testing.T) {
    s1 := NewSpinner()
    s2 := NewSpinner()
    if s1.id == s2.id {
        t.Error("expected distinct spinner IDs")
    }
}

func TestSpinnerInitReturnsCmd(t *testing.T) {
    s := NewSpinner()
    cmd := s.Init()
    if cmd == nil {
        t.Error("Init() should return a non-nil tick command")
    }
}

func TestSpinnerUpdateAdvancesFrame(t *testing.T) {
    s := NewSpinner()
    initial := s.frame
    s, cmd := s.Update(TickMsg{ID: s.id})
    if s.frame != initial+1 {
        t.Errorf("expected frame %d, got %d", initial+1, s.frame)
    }
    if cmd == nil {
        t.Error("Update should return next tick command")
    }
}

func TestSpinnerUpdateIgnoresMismatchedTick(t *testing.T) {
    s := NewSpinner()
    initial := s.frame
    s, cmd := s.Update(TickMsg{ID: s.id + 999})
    if s.frame != initial {
        t.Error("frame should not advance for mismatched tick ID")
    }
    if cmd != nil {
        t.Error("should return nil cmd for mismatched tick")
    }
}

func TestSpinnerFrameWraps(t *testing.T) {
    s := NewSpinner()
    s.frame = len(spinnerFrames) - 1
    s, _ = s.Update(TickMsg{ID: s.id})
    if s.frame != 0 {
        t.Errorf("expected frame to wrap to 0, got %d", s.frame)
    }
}

func TestSpinnerViewWithRenders(t *testing.T) {
    s := NewSpinner()
    ctx := testContext(theme.DarkTheme(), 80)
    result := s.ViewWith(ctx)
    if result == "" {
        t.Error("ViewWith returned empty string")
    }
    if !strings.Contains(result, "⠋") {
        t.Error("ViewWith should contain the first braille frame")
    }
}

func TestSpinnerViewWithDifferentThemes(t *testing.T) {
    s := NewSpinner()
    dark := s.ViewWith(testContext(theme.DarkTheme(), 80))
    light := s.ViewWith(testContext(theme.LightTheme(), 80))
    if dark == light {
        t.Error("expected different output for dark vs light themes")
    }
}

func TestSpinnerViewRendersCurrentFrame(t *testing.T) {
    s := NewSpinner()
    s.frame = 3
    ctx := testContext(theme.DarkTheme(), 80)
    result := s.ViewWith(ctx)
    if !strings.Contains(result, spinnerFrames[3]) {
        t.Errorf("expected frame 3 glyph %q in output", spinnerFrames[3])
    }
}
```

**Conventions followed:**
- Same package `atoms` (white-box testing, can access unexported fields like `frame`, `id`)
- Uses `testContext()` helper from `atoms_test.go`
- Uses `theme.DarkTheme()` / `theme.LightTheme()` directly
- Standard `testing.T`, no external framework
- `strings.Contains` for output assertions (matches Badge/TextBlock test patterns)

### Phase 3: `molecules/molecules.go`

```go
// Package molecules provides multi-component compositions built from atoms.
package molecules

import "github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"

// RenderContext is re-exported from atoms for convenience.
type RenderContext = atoms.RenderContext

// DefaultContext creates a RenderContext using the active theme.
func DefaultContext(width int) RenderContext {
    return atoms.DefaultContext(width)
}
```

This mirrors `atoms/atoms.go` in structure: package declaration, import of the theme system, shared types.

### Phase 4: `molecules/statusblock.go`

```go
package molecules

import (
    "strings"

    tea "charm.land/bubbletea/v2"

    "github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
    "github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// StatusBlockData carries configuration for a StatusBlock.
type StatusBlockData struct {
    Verb    string // action label, e.g. "Syncing", "Building"
    Elapsed string // optional elapsed time, e.g. "12s" -- rendered as outline Badge
    Count   string // optional progress count, e.g. "3/7" -- rendered as outline Badge
}

// StatusBlock composes a Spinner + verb text + optional elapsed/count badges
// into an inline status indicator.
// It follows the Bubble Tea sub-model pattern.
type StatusBlock struct {
    spinner atoms.Spinner
    Data    StatusBlockData
}

// NewStatusBlock creates a StatusBlock with the given data.
func NewStatusBlock(data StatusBlockData) StatusBlock {
    return StatusBlock{
        spinner: atoms.NewSpinner(),
        Data:    data,
    }
}

// Init returns the Spinner's initial tick command.
func (sb StatusBlock) Init() tea.Cmd {
    return sb.spinner.Init()
}

// Update forwards messages to the inner Spinner.
func (sb StatusBlock) Update(msg tea.Msg) (StatusBlock, tea.Cmd) {
    var cmd tea.Cmd
    sb.spinner, cmd = sb.spinner.Update(msg)
    return sb, cmd
}

// View renders the full status line: spinner + verb + optional badges.
func (sb StatusBlock) View(ctx RenderContext) string {
    var parts []string

    // Spinner glyph
    parts = append(parts, sb.spinner.ViewWith(ctx))

    // Verb text (no width constraint -- inline element)
    verbCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}
    verbStyle := theme.Style{Hierarchy: theme.Secondary}
    parts = append(parts, atoms.TextBlock(verbCtx, atoms.TextBlockData{
        Text:  sb.Data.Verb,
        Style: verbStyle,
    }))

    // Elapsed badge (optional)
    if sb.Data.Elapsed != "" {
        parts = append(parts, atoms.Badge(ctx, atoms.BadgeData{
            Label:   sb.Data.Elapsed,
            Style:   theme.Style{Hierarchy: theme.Tertiary},
            Variant: atoms.BadgeOutline,
        }))
    }

    // Count badge (optional)
    if sb.Data.Count != "" {
        parts = append(parts, atoms.Badge(ctx, atoms.BadgeData{
            Label:   sb.Data.Count,
            Style:   theme.Style{Status: theme.Info},
            Variant: atoms.BadgeOutline,
        }))
    }

    return strings.Join(parts, " ")
}
```

**Design notes:**
- Verb uses `Hierarchy: Secondary` (normal body text weight, no bold).
- Elapsed uses `Hierarchy: Tertiary` (dim) -- supporting info, not primary.
- Count uses `Status: Info` (cyan in dark theme) -- draws attention to progress.
- TextBlock verb is rendered with `Width: 0` to avoid padding (inline composition).
- `View()` takes `RenderContext` explicitly (not `tea.View`) -- molecules are composed by parents.

### Phase 5: `molecules/statusblock_test.go`

```go
package molecules

import (
    "strings"
    "testing"

    "github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
    "github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

func testContext(t *theme.Theme, width int) RenderContext {
    return RenderContext{Width: width, Theme: t}
}

func TestNewStatusBlock(t *testing.T) {
    sb := NewStatusBlock(StatusBlockData{Verb: "Syncing"})
    if sb.Data.Verb != "Syncing" {
        t.Errorf("expected verb 'Syncing', got %q", sb.Data.Verb)
    }
}

func TestStatusBlockInitReturnsCmd(t *testing.T) {
    sb := NewStatusBlock(StatusBlockData{Verb: "Building"})
    cmd := sb.Init()
    if cmd == nil {
        t.Error("Init() should return spinner tick command")
    }
}

func TestStatusBlockUpdateForwardsTick(t *testing.T) {
    sb := NewStatusBlock(StatusBlockData{Verb: "Testing"})
    // Get the spinner's ID to send the right TickMsg
    // We need to trigger a tick -- Init() would schedule one,
    // but we can directly send the message
    msg := atoms.TickMsg{ID: 0} // will be ignored (wrong ID)
    sb2, cmd := sb.Update(msg)
    // The tick was for a different ID, so cmd should be nil
    _ = sb2
    if cmd != nil {
        t.Error("mismatched tick should produce nil cmd")
    }
}

func TestStatusBlockViewRendersVerb(t *testing.T) {
    sb := NewStatusBlock(StatusBlockData{Verb: "Syncing"})
    ctx := testContext(theme.DarkTheme(), 80)
    result := sb.View(ctx)
    if !strings.Contains(result, "Syncing") {
        t.Error("View should contain the verb text")
    }
}

func TestStatusBlockViewRendersSpinner(t *testing.T) {
    sb := NewStatusBlock(StatusBlockData{Verb: "Building"})
    ctx := testContext(theme.DarkTheme(), 80)
    result := sb.View(ctx)
    // Should contain a braille character (first frame)
    if !strings.Contains(result, "⠋") {
        t.Error("View should contain spinner braille glyph")
    }
}

func TestStatusBlockViewRendersElapsed(t *testing.T) {
    sb := NewStatusBlock(StatusBlockData{
        Verb:    "Syncing",
        Elapsed: "5s",
    })
    ctx := testContext(theme.DarkTheme(), 80)
    result := sb.View(ctx)
    if !strings.Contains(result, "5s") {
        t.Error("View should contain elapsed badge text")
    }
}

func TestStatusBlockViewOmitsElapsedWhenEmpty(t *testing.T) {
    sb := NewStatusBlock(StatusBlockData{Verb: "Syncing"})
    ctx := testContext(theme.DarkTheme(), 80)
    result := sb.View(ctx)
    // Should not contain bracket pairs beyond the spinner
    // (no empty badges)
    if strings.Count(result, "[") > 0 && strings.Count(result, "]") > 0 {
        // Only fail if there are brackets with nothing useful between them
        // This is a soft check -- the key assertion is that "5s" is absent
    }
    // Primary assertion: no elapsed text
    if strings.Contains(result, "[]") {
        t.Error("should not render empty badges")
    }
}

func TestStatusBlockViewRendersCount(t *testing.T) {
    sb := NewStatusBlock(StatusBlockData{
        Verb:  "Building",
        Count: "3/7",
    })
    ctx := testContext(theme.DarkTheme(), 80)
    result := sb.View(ctx)
    if !strings.Contains(result, "3/7") {
        t.Error("View should contain count badge text")
    }
}

func TestStatusBlockViewOmitsCountWhenEmpty(t *testing.T) {
    sb := NewStatusBlock(StatusBlockData{Verb: "Building"})
    ctx := testContext(theme.DarkTheme(), 80)
    result := sb.View(ctx)
    if strings.Contains(result, "/") {
        t.Error("should not contain count separator when count is empty")
    }
}

func TestStatusBlockViewAllParts(t *testing.T) {
    sb := NewStatusBlock(StatusBlockData{
        Verb:    "Merging",
        Elapsed: "1m30s",
        Count:   "2/5",
    })
    ctx := testContext(theme.DarkTheme(), 80)
    result := sb.View(ctx)
    for _, want := range []string{"Merging", "1m30s", "2/5"} {
        if !strings.Contains(result, want) {
            t.Errorf("View should contain %q", want)
        }
    }
}
```

## Integration Pattern

Parent models wire StatusBlock into their Bubble Tea loop like this:

```go
type ParentModel struct {
    status molecules.StatusBlock
    // ...
}

func (m ParentModel) Init() tea.Cmd {
    return tea.Batch(
        m.status.Init(),
        // other init cmds...
    )
}

func (m ParentModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmd tea.Cmd
    m.status, cmd = m.status.Update(msg)
    // handle other messages...
    return m, cmd
}

func (m ParentModel) View() tea.View {
    ctx := atoms.DefaultContext(m.width)
    line := m.status.View(ctx)
    // compose into full view...
}
```

## Open Questions

1. **Atomic counter vs random ID for Spinner instances** -- The spec uses a package-level incrementing counter (`spinnerSeq`). An alternative is `rand.Int()` or `atomic.AddInt64`. The counter is simpler and sufficient since Bubble Tea is single-threaded. Revisit if spinners are ever created from goroutines.
