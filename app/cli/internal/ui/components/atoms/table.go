package atoms

import (
	"charm.land/lipgloss/v2"
	"charm.land/lipgloss/v2/table"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// TableAlignment represents the text alignment for a table column.
type TableAlignment int

const (
	AlignLeft TableAlignment = iota
	AlignCenter
	AlignRight
)

// TableData carries the data for rendering a table.
type TableData struct {
	Headers    []string
	Rows       [][]string
	Alignments []TableAlignment
}

// Table renders a styled table using lipgloss/v2/table.
// It produces a rounded-border table with themed colors and width awareness.
func Table(ctx RenderContext, data TableData) string {
	if len(data.Headers) == 0 && len(data.Rows) == 0 {
		return ""
	}

	headerStyle := ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Secondary})
	cellStyle := ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Secondary})
	borderStyle := lipgloss.NewStyle().Foreground(ctx.Theme.DimColor)

	// Map alignments to lipgloss positions for use in StyleFunc.
	colAligns := make([]lipgloss.Position, len(data.Alignments))
	for i, a := range data.Alignments {
		switch a {
		case AlignCenter:
			colAligns[i] = lipgloss.Center
		case AlignRight:
			colAligns[i] = lipgloss.Right
		default:
			colAligns[i] = lipgloss.Left
		}
	}

	t := table.New().
		Headers(data.Headers...).
		Rows(data.Rows...).
		Border(lipgloss.RoundedBorder()).
		BorderStyle(borderStyle).
		StyleFunc(func(row, col int) lipgloss.Style {
			var s lipgloss.Style
			if row == table.HeaderRow {
				s = headerStyle
			} else {
				s = cellStyle
			}
			s = s.Padding(0, 1)

			// Apply column alignment if available.
			if col < len(colAligns) {
				s = s.Align(colAligns[col])
			}
			return s
		})

	if ctx.Width > 0 {
		t = t.Width(ctx.Width)
	}

	return t.Render()
}
