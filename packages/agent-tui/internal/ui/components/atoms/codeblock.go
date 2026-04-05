package atoms

import (
	"fmt"
	"strings"

	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// CodeBlockData carries the data for a multi-line code block.
type CodeBlockData struct {
	Code        string
	Language    string // displayed as a dim label above the block
	LineNumbers bool
}

// CodeBlock renders a multi-line code block with an optional language label,
// optional line numbers, and a left-border gutter for visual distinction.
func CodeBlock(ctx RenderContext, data CodeBlockData) string {
	var parts []string

	labelStyle := ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Tertiary})
	codeStyle := ctx.Theme.Resolve(theme.Style{Category: theme.CatTool, Hierarchy: theme.Secondary})
	lineNumStyle := ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Quaternary})
	gutterStyle := ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Tertiary})

	// Language label above the block
	if data.Language != "" {
		parts = append(parts, labelStyle.Render(data.Language))
	}

	lines := strings.Split(data.Code, "\n")
	gutterChar := gutterStyle.Render("\u2502 ")

	// Calculate line number width for padding
	lineNumWidth := 0
	if data.LineNumbers {
		lineNumWidth = len(fmt.Sprintf("%d", len(lines)))
	}

	for i, line := range lines {
		var row strings.Builder
		row.WriteString(gutterChar)

		if data.LineNumbers {
			num := fmt.Sprintf("%*d ", lineNumWidth, i+1)
			row.WriteString(lineNumStyle.Render(num))
		}

		row.WriteString(codeStyle.Render(line))
		parts = append(parts, row.String())
	}

	return strings.Join(parts, "\n")
}
