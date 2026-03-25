package theme

import "charm.land/lipgloss/v2"

var (
	active *Theme
	themes map[string]*Theme
)

func init() {
	themes = map[string]*Theme{
		"dark":  DarkTheme(),
		"light": LightTheme(),
	}
	active = themes["dark"]
}

// Active returns the currently active theme.
func Active() *Theme {
	return active
}

// SetActive switches the active theme by name.
func SetActive(name string) {
	if t, ok := themes[name]; ok {
		active = t
	}
}

// Register adds a custom theme to the registry.
func Register(t *Theme) {
	themes[t.Name] = t
}

// Resolve is a convenience that resolves a Style against the active theme.
func Resolve(s Style) lipgloss.Style {
	return active.Resolve(s)
}

// Dim returns a style using the active theme's dim/muted color.
func Dim() lipgloss.Style {
	return lipgloss.NewStyle().Foreground(active.DimColor)
}

// Fg returns a style using the active theme's foreground color.
func Fg() lipgloss.Style {
	return lipgloss.NewStyle().Foreground(active.Foreground)
}

// Bold returns a bold style using the active theme's foreground color.
func Bold() lipgloss.Style {
	return lipgloss.NewStyle().Bold(true).Foreground(active.Foreground)
}
