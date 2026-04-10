package theme

import (
	embedded "github.com/dugshub/agentic-tui/themes"
)

// DarkTheme returns a pastel dark terminal theme.
func DarkTheme() *Theme {
	t, err := LoadThemeFromYAML(embedded.DarkYAML)
	if err != nil {
		panic("load embedded dark theme: " + err.Error())
	}
	return t
}

// LightTheme returns a light terminal theme.
func LightTheme() *Theme {
	t, err := LoadThemeFromYAML(embedded.LightYAML)
	if err != nil {
		panic("load embedded light theme: " + err.Error())
	}
	return t
}
