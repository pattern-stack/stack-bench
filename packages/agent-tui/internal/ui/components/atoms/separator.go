package atoms

import (
	"strings"

	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// Separator renders a full-width horizontal rule using box-drawing characters.
func Separator(ctx RenderContext) string {
	style := ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Tertiary})
	line := strings.Repeat("\u2500", ctx.Width)
	return style.Render(line)
}
