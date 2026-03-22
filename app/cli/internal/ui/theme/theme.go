package theme

import (
	"image/color"

	"charm.land/lipgloss/v2"
)

// Theme maps design tokens to lipgloss styles.
type Theme struct {
	Name        string
	Categories  [9]color.Color
	Statuses    [7]color.Color // indexed by Status (0=NoStatus is unused)
	Foreground  color.Color
	Background  color.Color
	DimColor    color.Color
}

// Resolve converts a token Style into a lipgloss.Style.
func (t *Theme) Resolve(s Style) lipgloss.Style {
	st := lipgloss.NewStyle()

	// Status overrides category for foreground color
	if s.Status != NoStatus {
		st = st.Foreground(t.Statuses[s.Status])
	} else if s.Category == CatDefault {
		st = st.Foreground(t.Foreground)
	} else {
		st = st.Foreground(t.Categories[s.Category])
	}

	// Hierarchy affects opacity/dimness
	switch s.Hierarchy {
	case Primary:
		// Primary is just normal weight — use Strong emphasis for bold
	case Tertiary:
		st = st.Foreground(t.DimColor)
	case Quaternary:
		st = st.Foreground(t.DimColor).Italic(true)
	}

	// Emphasis modifies weight
	switch s.Emphasis {
	case Strong:
		st = st.Bold(true)
	case Subtle:
		if s.Status == NoStatus && s.Category == CatDefault && s.Hierarchy < Tertiary {
			st = st.Foreground(t.DimColor)
		}
	}

	return st
}
