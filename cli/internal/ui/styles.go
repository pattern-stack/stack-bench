package ui

import "github.com/charmbracelet/lipgloss"

// Colors used throughout the CLI.
var (
	ColorAccent = lipgloss.AdaptiveColor{Light: "#7D56F4", Dark: "#BD93F9"}
	ColorGreen  = lipgloss.AdaptiveColor{Light: "#2E7D32", Dark: "#50FA7B"}
	ColorRed    = lipgloss.AdaptiveColor{Light: "#C62828", Dark: "#FF5555"}
	ColorDim    = lipgloss.AdaptiveColor{Light: "#999999", Dark: "#6272A4"}
	ColorFg     = lipgloss.AdaptiveColor{Light: "#282A36", Dark: "#F8F8F2"}
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
