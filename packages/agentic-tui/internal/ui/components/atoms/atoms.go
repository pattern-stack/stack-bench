package atoms

import "github.com/dugshub/agentic-tui/internal/ui/theme"

// Role identifies the author of a message in the chat system.
type Role int

const (
	RoleUser      Role = iota // Human user
	RoleAssistant             // AI assistant
	RoleSystem                // System messages
)

// RenderContext carries shared state for all render functions.
// Using a struct keeps function signatures stable as we add capabilities.
type RenderContext struct {
	Width int
	Theme *theme.Theme
}

// DefaultContext creates a RenderContext using the active theme.
func DefaultContext(width int) RenderContext {
	return RenderContext{Width: width, Theme: theme.Active()}
}
