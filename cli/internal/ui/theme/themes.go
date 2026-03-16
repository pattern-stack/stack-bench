package theme

import (
	"image/color"

	"charm.land/lipgloss/v2"
)

// c is a shorthand for lipgloss.Color.
func c(hex string) color.Color {
	return lipgloss.Color(hex)
}

// DarkTheme returns a Dracula-inspired dark terminal theme.
func DarkTheme() *Theme {
	return &Theme{
		Name: "dark",
		Categories: [8]color.Color{
			CatAgent:  c("#BD93F9"), // purple
			CatSystem: c("#8BE9FD"), // cyan
			CatTool:   c("#FFB86C"), // orange
			CatUser:   c("#F8F8F2"), // foreground
			Cat5:      c("#FF79C6"), // pink
			Cat6:      c("#F1FA8C"), // yellow
			Cat7:      c("#50FA7B"), // green
			Cat8:      c("#6272A4"), // comment
		},
		Statuses: [7]color.Color{
			NoStatus: c("#F8F8F2"),
			Success:  c("#50FA7B"),
			Error:    c("#FF5555"),
			Warning:  c("#F1FA8C"),
			Info:     c("#8BE9FD"),
			Muted:    c("#6272A4"),
			Running:  c("#BD93F9"),
		},
		Foreground: c("#F8F8F2"),
		Background: c("#282A36"),
		DimColor:   c("#6272A4"),
	}
}

// LightTheme returns a light terminal theme.
func LightTheme() *Theme {
	return &Theme{
		Name: "light",
		Categories: [8]color.Color{
			CatAgent:  c("#7D56F4"), // purple
			CatSystem: c("#0077B6"), // blue
			CatTool:   c("#E85D04"), // orange
			CatUser:   c("#282A36"), // dark text
			Cat5:      c("#C62828"), // red
			Cat6:      c("#827717"), // olive
			Cat7:      c("#2E7D32"), // green
			Cat8:      c("#999999"), // gray
		},
		Statuses: [7]color.Color{
			NoStatus: c("#282A36"),
			Success:  c("#2E7D32"),
			Error:    c("#C62828"),
			Warning:  c("#F57F17"),
			Info:     c("#0077B6"),
			Muted:    c("#999999"),
			Running:  c("#7D56F4"),
		},
		Foreground: c("#282A36"),
		Background: c("#FFFFFF"),
		DimColor:   c("#999999"),
	}
}
