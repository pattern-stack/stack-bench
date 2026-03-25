package atoms

import "github.com/dugshub/stack-bench/app/cli/internal/ui/theme"

// Role identifies the author of a message in the chat system.
type Role int

const (
	RoleUser      Role = iota // Human user
	RoleAssistant             // AI assistant
	RoleSystem                // System messages
)

// CompactThreshold is the width (in columns) below which components
// switch to compact layout. Discovered through testing; start at 72.
const CompactThreshold = 72

// RenderContext carries shared state for all render functions.
// Using a struct keeps function signatures stable as we add capabilities.
type RenderContext struct {
	Width int
	Theme *theme.Theme
}

// Compact reports whether the current width is below the compact threshold.
// Components should use this to switch to condensed layouts.
// Returns false when Width is 0 (zero-width contexts are inline/unconstrained).
func (ctx RenderContext) Compact() bool {
	return ctx.Width > 0 && ctx.Width < CompactThreshold
}

// DefaultContext creates a RenderContext using the active theme.
func DefaultContext(width int) RenderContext {
	return RenderContext{Width: width, Theme: theme.Active()}
}
