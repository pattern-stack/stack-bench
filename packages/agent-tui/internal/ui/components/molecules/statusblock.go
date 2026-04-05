package molecules

import (
	"strings"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/agent-tui/internal/ui/components/atoms"
	"github.com/dugshub/agent-tui/internal/ui/theme"
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

	// Elapsed and count badges are hidden in compact mode
	if !ctx.Compact() {
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
	}

	return strings.Join(parts, " ")
}
