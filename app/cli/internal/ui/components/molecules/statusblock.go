package molecules

import (
	"fmt"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// StatusBlockData holds parameters for rendering a status indicator.
type StatusBlockData struct {
	Spinner atoms.Spinner
	Verb    string // e.g. "Reading", "Analyzing"
	Elapsed float64 // seconds, 0 = omit
	Count   int     // e.g. files processed, 0 = omit
	Unit    string  // e.g. "files", "lines"
}

// StatusBlock renders a spinner with a verb and optional elapsed/count badges.
// Layout: ⠋ Reading  [3.2s]  [12 files]
func StatusBlock(ctx atoms.RenderContext, data StatusBlockData) string {
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	spinner := data.Spinner.View(inlineCtx)

	verb := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
		Text:  data.Verb,
		Style: theme.Style{Hierarchy: theme.Secondary},
	})

	result := spinner + " " + verb

	if data.Elapsed > 0 {
		label := fmt.Sprintf("%.1fs", data.Elapsed)
		badge := atoms.Badge(inlineCtx, atoms.BadgeData{
			Label:   label,
			Style:   theme.Style{Hierarchy: theme.Tertiary},
			Variant: atoms.BadgeOutline,
		})
		result += "  " + badge
	}

	if data.Count > 0 && data.Unit != "" {
		label := fmt.Sprintf("%d %s", data.Count, data.Unit)
		badge := atoms.Badge(inlineCtx, atoms.BadgeData{
			Label:   label,
			Style:   theme.Style{Hierarchy: theme.Tertiary},
			Variant: atoms.BadgeOutline,
		})
		result += "  " + badge
	}

	return result
}
