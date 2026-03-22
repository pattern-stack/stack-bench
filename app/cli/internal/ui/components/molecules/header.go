package molecules

import (
	"strings"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// HeaderData holds parameters for rendering a page/section header.
type HeaderData struct {
	Title  string
	Badges []atoms.BadgeData
}

// Header renders a title with optional badges and a separator line beneath.
func Header(ctx atoms.RenderContext, data HeaderData) string {
	var parts []string

	// Title renders inline (no width padding) so badges sit beside it
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}
	title := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
		Text:  data.Title,
		Style: theme.Style{Hierarchy: theme.Primary, Emphasis: theme.Strong},
	})
	parts = append(parts, title)

	if len(data.Badges) > 0 {
		var badges []string
		for _, bd := range data.Badges {
			badges = append(badges, atoms.Badge(ctx, bd))
		}
		parts = append(parts, strings.Join(badges, " "))
	}

	header := strings.Join(parts, "  ")
	sep := atoms.Separator(ctx)

	return header + "\n" + sep
}
