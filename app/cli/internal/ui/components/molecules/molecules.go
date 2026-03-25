// Package molecules provides multi-component compositions built from atoms.
package molecules

import "github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"

// RenderContext is re-exported from atoms for convenience.
type RenderContext = atoms.RenderContext

// DefaultContext creates a RenderContext using the active theme.
func DefaultContext(width int) RenderContext {
	return atoms.DefaultContext(width)
}
