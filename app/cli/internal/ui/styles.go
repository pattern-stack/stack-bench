package ui

import (
	"charm.land/lipgloss/v2"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// Convenience styles resolved from the active theme.
// These exist for backward compatibility — new code should use theme.Resolve() directly.
var (
	Dim    = lipgloss.NewStyle().Foreground(theme.Active().DimColor)
	Fg     = lipgloss.NewStyle().Foreground(theme.Active().Foreground)
	Bold   = lipgloss.NewStyle().Bold(true).Foreground(theme.Active().Foreground)
	Green  = theme.Resolve(theme.Style{Status: theme.Success})
	Red    = theme.Resolve(theme.Style{Status: theme.Error})
	Accent = theme.Resolve(theme.Style{Category: theme.CatAgent})
)

// MaxI returns the larger of two integers.
func MaxI(a, b int) int {
	if a > b {
		return a
	}
	return b
}
