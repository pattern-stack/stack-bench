package molecules

import (
	"github.com/dugshub/agentic-tui/internal/ui/components/atoms"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

// ConfirmPromptData holds parameters for rendering a binary yes/no prompt.
type ConfirmPromptData struct {
	Question string
	Selected bool // true = yes selected, false = no selected
}

// ConfirmPrompt renders a question with highlighted yes/no options.
// State is managed by the caller — this is a pure render function.
func ConfirmPrompt(ctx atoms.RenderContext, data ConfirmPromptData) string {
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	question := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
		Text:  data.Question,
		Style: theme.Style{Hierarchy: theme.Primary},
	})

	var yesBadge, noBadge string
	if data.Selected {
		yesBadge = atoms.Badge(inlineCtx, atoms.BadgeData{
			Label:   "yes",
			Style:   theme.Style{Status: theme.Success},
			Variant: atoms.BadgeFilled,
		})
		noBadge = atoms.Badge(inlineCtx, atoms.BadgeData{
			Label:   "no",
			Style:   theme.Style{Hierarchy: theme.Tertiary},
			Variant: atoms.BadgeOutline,
		})
	} else {
		yesBadge = atoms.Badge(inlineCtx, atoms.BadgeData{
			Label:   "yes",
			Style:   theme.Style{Hierarchy: theme.Tertiary},
			Variant: atoms.BadgeOutline,
		})
		noBadge = atoms.Badge(inlineCtx, atoms.BadgeData{
			Label:   "no",
			Style:   theme.Style{Status: theme.Error},
			Variant: atoms.BadgeFilled,
		})
	}

	return question + "  " + yesBadge + " " + noBadge
}
