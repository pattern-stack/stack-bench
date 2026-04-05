package atoms

import (
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// BadgeVariant controls the visual mode of a badge.
type BadgeVariant int

const (
	BadgeFilled  BadgeVariant = iota // Background color from resolved style
	BadgeOutline                     // [label] with foreground color
)

// defaultBadgeMaxWidth is the maximum label width before truncation.
const defaultBadgeMaxWidth = 16

// BadgeData carries the data for a small inline label.
type BadgeData struct {
	Label    string
	Style    theme.Style
	Variant  BadgeVariant
	MaxWidth int // 0 = default (16 chars), truncates with ellipsis
}

// Badge renders a small inline label used for role indicators, status tags,
// language labels, and file types.
func Badge(ctx RenderContext, data BadgeData) string {
	maxWidth := data.MaxWidth
	if maxWidth <= 0 {
		maxWidth = defaultBadgeMaxWidth
	}

	label := data.Label
	if len(label) > maxWidth {
		label = label[:maxWidth-1] + "\u2026"
	}

	resolved := ctx.Theme.Resolve(data.Style)

	switch data.Variant {
	case BadgeFilled:
		fg := resolved.GetForeground()
		style := resolved.
			Background(fg).
			Foreground(ctx.Theme.Background).
			Padding(0, 1)
		return style.Render(label)

	case BadgeOutline:
		return resolved.Render("[" + label + "]")

	default:
		return resolved.Render(label)
	}
}
