package molecules

import (
	"strings"

	"github.com/dugshub/agent-tui/internal/ui/components/atoms"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// ToolCallState represents the execution state of a tool call.
type ToolCallState int

const (
	ToolCallPending ToolCallState = iota // Not yet started
	ToolCallRunning                      // Currently executing
	ToolCallSuccess                      // Completed successfully
	ToolCallError                        // Failed
)

// ToolCallBlockData holds parameters for rendering a tool call display.
type ToolCallBlockData struct {
	ToolName string
	Args     string        // optional: rendered argument summary
	State    ToolCallState
	Spinner  atoms.Spinner // used when State == ToolCallRunning
	Result   string        // optional: short result summary
}

// ToolCallBlock renders a tool invocation header with a state-appropriate icon,
// the tool name as a badge, optional arguments inline, and an optional short result.
// Rich bodies (diff/code/bash) should be rendered separately by the caller and
// composed below this header — see chat/view.go for the dispatch pattern.
func ToolCallBlock(ctx atoms.RenderContext, data ToolCallBlockData) string {
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	// State icon
	var icon string
	switch data.State {
	case ToolCallRunning:
		icon = data.Spinner.View(inlineCtx)
	case ToolCallSuccess:
		icon = atoms.Icon(inlineCtx, atoms.IconCheck, theme.Style{Status: theme.Success})
	case ToolCallError:
		icon = atoms.Icon(inlineCtx, atoms.IconX, theme.Style{Status: theme.Error})
	default:
		icon = atoms.Icon(inlineCtx, atoms.IconCircle, theme.Style{Hierarchy: theme.Tertiary})
	}

	// Tool name badge
	badge := atoms.Badge(inlineCtx, atoms.BadgeData{
		Label:   data.ToolName,
		Style:   theme.Style{Category: theme.CatTool},
		Variant: atoms.BadgeOutline,
	})

	line := icon + " " + badge

	// Optional arguments
	if data.Args != "" {
		args := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  data.Args,
			Style: theme.Style{Hierarchy: theme.Tertiary},
		})
		line += "  " + args
	}

	var parts []string
	parts = append(parts, line)

	// Optional result (indented below)
	if data.Result != "" {
		result := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  data.Result,
			Style: theme.Style{Hierarchy: theme.Secondary},
		})
		lines := strings.Split(result, "\n")
		for _, l := range lines {
			parts = append(parts, "    "+l)
		}
	}

	return strings.Join(parts, "\n")
}
