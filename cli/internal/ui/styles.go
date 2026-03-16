package ui

import "charm.land/lipgloss/v2"

// Colors used throughout the CLI.
// Default to dark theme; adaptive light/dark will come with the token system.
var (
	ColorAccent = lipgloss.Color("#BD93F9")
	ColorGreen  = lipgloss.Color("#50FA7B")
	ColorRed    = lipgloss.Color("#FF5555")
	ColorDim    = lipgloss.Color("#6272A4")
	ColorFg     = lipgloss.Color("#F8F8F2")
)

// Base text styles.
var (
	Dim    = lipgloss.NewStyle().Foreground(ColorDim)
	Fg     = lipgloss.NewStyle().Foreground(ColorFg)
	Bold   = lipgloss.NewStyle().Bold(true).Foreground(ColorFg)
	Green  = lipgloss.NewStyle().Foreground(ColorGreen)
	Red    = lipgloss.NewStyle().Foreground(ColorRed)
	Accent = lipgloss.NewStyle().Foreground(ColorAccent)
)
