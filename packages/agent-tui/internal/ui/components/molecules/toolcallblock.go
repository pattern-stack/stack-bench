package molecules

import (
	"strings"

	"github.com/dugshub/agent-tui/internal/ui/components/atoms"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// ToolStatus represents the current state of a tool invocation.
type ToolStatus int

const (
	ToolRunning ToolStatus = iota
	ToolSuccess
	ToolError
)

// ToolCallData carries configuration for a ToolCallBlock.
type ToolCallData struct {
	Name      string     // tool name, e.g. "edit_file"
	Status    ToolStatus // Running, Success, Error
	Input     string     // tool input/arguments (shown in collapsed CodeBlock)
	Output    string     // tool output/result (shown in collapsed CodeBlock)
	Error     string     // error message (shown when Status == ToolError)
	Collapsed bool       // if true, hide input/output CodeBlocks
}

// statusIcon returns the icon name for a given tool status.
func statusIcon(status ToolStatus) atoms.IconName {
	switch status {
	case ToolSuccess:
		return atoms.IconCheck
	case ToolError:
		return atoms.IconX
	default:
		return atoms.IconDot
	}
}

// statusTheme returns the theme status for a given tool status.
func statusTheme(status ToolStatus) theme.Status {
	switch status {
	case ToolSuccess:
		return theme.Success
	case ToolError:
		return theme.Error
	default:
		return theme.Running
	}
}

// statusLabel returns the display label for a given tool status.
func statusLabel(status ToolStatus) string {
	switch status {
	case ToolSuccess:
		return "done"
	case ToolError:
		return "failed"
	default:
		return "running"
	}
}

// ToolCallBlock renders a tool invocation display.
// Header: Icon(status) + Badge(tool name, filled, CatTool) + Badge(status label, outline, status color)
// Body (when not collapsed): CodeBlock(input) + CodeBlock(output) or error text
func ToolCallBlock(ctx atoms.RenderContext, data ToolCallData) string {
	var parts []string

	// --- Header line ---
	var header []string

	// Status icon
	themeStatus := statusTheme(data.Status)
	iconStyle := theme.Style{Status: themeStatus}
	header = append(header, atoms.Icon(ctx, statusIcon(data.Status), iconStyle))

	// Tool name badge (filled, CatTool)
	header = append(header, atoms.Badge(ctx, atoms.BadgeData{
		Label:   data.Name,
		Style:   theme.Style{Category: theme.CatTool},
		Variant: atoms.BadgeFilled,
	}))

	// Status label badge (outline, status color)
	header = append(header, atoms.Badge(ctx, atoms.BadgeData{
		Label:   statusLabel(data.Status),
		Style:   theme.Style{Status: themeStatus},
		Variant: atoms.BadgeOutline,
	}))

	parts = append(parts, strings.Join(header, " "))

	// --- Body (when not collapsed) ---
	if !data.Collapsed {
		// Error text
		if data.Status == ToolError && data.Error != "" {
			errStyle := theme.Style{Status: theme.Error}
			parts = append(parts, atoms.TextBlock(ctx, atoms.TextBlockData{
				Text:  data.Error,
				Style: errStyle,
			}))
		}

		// Input code block
		if data.Input != "" {
			parts = append(parts, atoms.CodeBlock(ctx, atoms.CodeBlockData{
				Code: data.Input,
			}))
		}

		// Output code block
		if data.Output != "" {
			parts = append(parts, atoms.CodeBlock(ctx, atoms.CodeBlockData{
				Code: data.Output,
			}))
		}
	}

	return strings.Join(parts, "\n")
}
