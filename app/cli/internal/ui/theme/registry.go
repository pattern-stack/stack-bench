package theme

import (
	"os"

	"charm.land/lipgloss/v2"
)

var (
	active *Theme
	themes map[string]*Theme
)

func init() {
	themes = map[string]*Theme{
		"dark":  DarkTheme(),
		"light": LightTheme(),
	}
	if lipgloss.HasDarkBackground(os.Stdin, os.Stdout) {
		active = themes["dark"]
	} else {
		active = themes["light"]
	}
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
