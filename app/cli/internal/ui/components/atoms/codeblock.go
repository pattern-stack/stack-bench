package atoms

import (
	"fmt"
	"strings"

	"charm.land/lipgloss/v2"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// CodeBlockData carries the data for a multi-line code block.
type CodeBlockData struct {
	Code        string
	Language    string // displayed in the header bar
	FilePath    string // optional file path shown in the header
	LineNumbers bool
}

// CodeBlock renders a multi-line code block with an optional language label,
// optional line numbers, and a left-border gutter for visual distinction.
// Code is never word-wrapped — lines that exceed width are truncated.
func CodeBlock(ctx RenderContext, data CodeBlockData) string {
	var parts []string

	labelStyle := ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Tertiary})
	codeStyle := ctx.Theme.Resolve(theme.Style{Category: theme.CatTool, Hierarchy: theme.Secondary})
	lineNumStyle := ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Quaternary})
	gutterStyle := ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Tertiary})

	// Blank line before block
	parts = append(parts, "")

	// Header bar: language badge (left) + file path (right)
	if data.Language != "" || data.FilePath != "" {
		var headerParts []string
		if data.Language != "" {
			headerParts = append(headerParts, labelStyle.Render(data.Language))
		}
		if data.FilePath != "" {
			pathStyle := ctx.Theme.Resolve(theme.Style{Category: theme.CatTool, Hierarchy: theme.Tertiary})
			headerParts = append(headerParts, pathStyle.Render(data.FilePath))
		}
		parts = append(parts, "  "+strings.Join(headerParts, "  "))
	}

	lines := strings.Split(data.Code, "\n")
	gutterChar := gutterStyle.Render("  │ ")

	// Calculate line number width for padding
	lineNumWidth := 0
	if data.LineNumbers {
		lineNumWidth = len(fmt.Sprintf("%d", len(lines)))
	}

	// Max content width (account for gutter + padding)
	gutterWidth := 4 // "  │ "
	if data.LineNumbers {
		gutterWidth += lineNumWidth + 1
	}
	maxContentWidth := 0
	if ctx.Width > gutterWidth {
		maxContentWidth = ctx.Width - gutterWidth
	}

	// Syntax-highlight the code if a language is set; otherwise use flat style.
	var highlightedLines []string
	if data.Language != "" {
		highlighted := HighlightCode(ctx, data.Code, data.Language)
		highlightedLines = strings.Split(highlighted, "\n")
	}

	for i, line := range lines {
		var row strings.Builder
		row.WriteString(gutterChar)

		if data.LineNumbers {
			num := fmt.Sprintf("%*d ", lineNumWidth, i+1)
			row.WriteString(lineNumStyle.Render(num))
		}

		// Get the content for this line
		var content string
		if highlightedLines != nil && i < len(highlightedLines) {
			content = highlightedLines[i]
		} else {
			content = codeStyle.Render(line)
		}

		// Truncate if it would exceed width (code never wraps)
		if maxContentWidth > 0 {
			content = lipgloss.NewStyle().MaxWidth(maxContentWidth).Render(content)
		}

		row.WriteString(content)
		parts = append(parts, row.String())
	}

	// Blank line after block
	parts = append(parts, "")

	return strings.Join(parts, "\n")
}
