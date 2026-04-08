package molecules

import (
	"strings"

	"github.com/dugshub/agent-tui/internal/ui/components/atoms"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// ErrorBlockData holds parameters for rendering an error display.
type ErrorBlockData struct {
	Title       string
	Message     string
	Suggestions []string
}

// ErrorBlock renders an error badge, message, and optional suggestions.
func ErrorBlock(ctx atoms.RenderContext, data ErrorBlockData) string {
	title := data.Title
	if title == "" {
		title = "error"
	}

	badge := atoms.Badge(ctx, atoms.BadgeData{
		Label:   title,
		Style:   theme.Style{Status: theme.Error},
		Variant: atoms.BadgeFilled,
	})

	message := atoms.TextBlock(ctx, atoms.TextBlockData{
		Text:  data.Message,
		Style: theme.Style{Status: theme.Error},
	})

	result := badge + "\n" + "  " + message

	if len(data.Suggestions) > 0 {
		var lines []string
		for _, s := range data.Suggestions {
			lines = append(lines, "  - "+s)
		}
		suggestions := atoms.TextBlock(ctx, atoms.TextBlockData{
			Text:  strings.Join(lines, "\n"),
			Style: theme.Style{Hierarchy: theme.Tertiary},
		})
		result += "\n" + suggestions
	}

	return result
}
