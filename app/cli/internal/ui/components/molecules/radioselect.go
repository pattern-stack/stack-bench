package molecules

import (
	"strings"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// RadioOption describes a single selectable item.
type RadioOption struct {
	Label       string
	Description string
}

// RadioSelectData holds parameters for rendering a radio selection list.
type RadioSelectData struct {
	Label    string
	Options  []RadioOption
	Selected int // index of the currently selected option
}

// RadioSelect renders a label with a list of options, highlighting the selected one.
// State is managed by the caller — this is a pure render function.
func RadioSelect(ctx atoms.RenderContext, data RadioSelectData) string {
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	var parts []string

	if data.Label != "" {
		label := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  data.Label,
			Style: theme.Style{Hierarchy: theme.Primary},
		})
		parts = append(parts, label)
	}

	for i, opt := range data.Options {
		var icon string
		var labelStyle theme.Style
		var descStyle theme.Style

		if i == data.Selected {
			icon = atoms.Icon(inlineCtx, atoms.IconCursor, theme.Style{Category: theme.CatAgent})
			labelStyle = theme.Style{Category: theme.CatAgent, Emphasis: theme.Strong}
			descStyle = theme.Style{Hierarchy: theme.Secondary}
		} else {
			icon = atoms.Icon(inlineCtx, atoms.IconCircle, theme.Style{Hierarchy: theme.Tertiary})
			labelStyle = theme.Style{Hierarchy: theme.Secondary}
			descStyle = theme.Style{Hierarchy: theme.Tertiary}
		}

		label := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  opt.Label,
			Style: labelStyle,
		})

		line := "  " + icon + " " + label
		if opt.Description != "" {
			desc := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text:  opt.Description,
				Style: descStyle,
			})
			line += "  " + desc
		}

		parts = append(parts, line)
	}

	return strings.Join(parts, "\n")
}
