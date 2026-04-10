package atoms

import "github.com/dugshub/agentic-tui/internal/ui/theme"

// InlineCode renders a short code span for embedding within flowing text.
// Unlike CodeBlock, it produces no newlines and is meant to be inline.
func InlineCode(ctx RenderContext, code string) string {
	style := ctx.Theme.Resolve(theme.Style{
		Status:    theme.Success,
		Hierarchy: theme.Secondary,
	})
	return style.Render(code)
}
