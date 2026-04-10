package atoms

import "github.com/dugshub/agentic-tui/internal/ui/theme"

// TextBlockData carries the data for a styled text span.
type TextBlockData struct {
	Text  string
	Style theme.Style
}

// TextBlock renders a string with a resolved theme.Style.
// This is the fundamental atom -- most other components delegate to it.
func TextBlock(ctx RenderContext, data TextBlockData) string {
	style := ctx.Theme.Resolve(data.Style)
	if ctx.Width > 0 {
		style = style.Width(ctx.Width)
	}
	return style.Render(data.Text)
}
