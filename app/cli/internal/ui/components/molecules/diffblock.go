package molecules

import (
	"strings"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// DiffBlockData holds parameters for rendering a unified diff display.
type DiffBlockData struct {
	FilePath string
	Diff     string // unified diff content (lines starting with +, -, or space)
}

// DiffBlock renders a file path header and color-coded diff lines.
// Added lines are green, removed lines are red, context lines are dim.
func DiffBlock(ctx atoms.RenderContext, data DiffBlockData) string {
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	var parts []string

	// File path header
	if data.FilePath != "" {
		path := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  data.FilePath,
			Style: theme.Style{Category: theme.CatTool, Emphasis: theme.Strong},
		})
		parts = append(parts, path)
	}

	// Diff lines
	lines := strings.Split(data.Diff, "\n")
	for _, line := range lines {
		var style theme.Style
		switch {
		case strings.HasPrefix(line, "+"):
			style = theme.Style{Status: theme.Success}
		case strings.HasPrefix(line, "-"):
			style = theme.Style{Status: theme.Error}
		case strings.HasPrefix(line, "@@"):
			style = theme.Style{Category: theme.CatSystem, Hierarchy: theme.Tertiary}
		default:
			style = theme.Style{Hierarchy: theme.Tertiary}
		}

		rendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  line,
			Style: style,
		})
		parts = append(parts, "  "+rendered)
	}

	return strings.Join(parts, "\n")
}
