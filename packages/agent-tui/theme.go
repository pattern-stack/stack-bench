package tui

import (
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// Re-export theme types for public API.
type Theme = theme.Theme
type Style = theme.Style
type Category = theme.Category
type Hierarchy = theme.Hierarchy
type Emphasis = theme.Emphasis
type Status = theme.Status

// Re-export theme constants.
const (
	CatAgent  = theme.CatAgent
	CatSystem = theme.CatSystem
	CatTool   = theme.CatTool
	CatUser   = theme.CatUser

	Primary    = theme.Primary
	Secondary  = theme.Secondary
	Tertiary   = theme.Tertiary
	Quaternary = theme.Quaternary

	Strong = theme.Strong
	Normal = theme.Normal
	Subtle = theme.Subtle

	NoStatus = theme.NoStatus
	Success  = theme.Success
	Error    = theme.Error
	Warning  = theme.Warning
	Info     = theme.Info
	Muted    = theme.Muted
	Running  = theme.Running
)

// DarkTheme returns a Dracula-inspired dark terminal theme.
func DarkTheme() *Theme {
	return theme.DarkTheme()
}

// LightTheme returns a light terminal theme.
func LightTheme() *Theme {
	return theme.LightTheme()
}
