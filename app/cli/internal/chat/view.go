package chat

import (
	"fmt"
	"strings"

	"charm.land/lipgloss/v2"

	"github.com/dugshub/stack-bench/app/cli/internal/ui"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/molecules"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// View renders the chat content area: viewport + status line + input.
// The app owns header (above) and legend (below).
func (m *Model) View() string {
	if m.width < 20 || m.height < 4 {
		return ""
	}

	ctx := atoms.DefaultContext(m.width)
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	// Calculate dynamic chrome heights before rendering the viewport.
	// Autocomplete and multiline input both consume vertical space.
	acView := m.autocomplete.View()
	acH := 0
	if acView != "" {
		acH = lipgloss.Height(acView)
	}

	// Input: build wrapped lines to know how tall the input area is.
	sep := atoms.Separator(ctx)
	label := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
		Text:  "you:",
		Style: theme.Style{Hierarchy: theme.Tertiary},
	})
	prefix := " " + label + " "
	prefixW := lipgloss.Width(prefix)
	availW := m.width - prefixW
	if availW < 10 {
		availW = 10
	}
	inputLines := strings.Split(m.input+"_", "\n")
	var wrappedLines []string
	for _, line := range inputLines {
		wrappedLines = append(wrappedLines, wrapLine(line, availW)...)
	}
	extraInputLines := len(wrappedLines) - 1

	// Temporarily shrink viewport for autocomplete + extra input lines.
	chromeExtra := acH + extraInputLines
	if chromeExtra > 0 {
		origH := m.viewport.Height()
		adjusted := origH - chromeExtra
		if adjusted < 1 {
			adjusted = 1
		}
		m.viewport.SetHeight(adjusted)
		defer m.viewport.SetHeight(origH)
	}

	// Viewport
	body := m.viewport.View()

	// Status line
	var statusContent string
	if m.streaming {
		statusContent = atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  "  ...",
			Style: theme.Style{Category: theme.CatAgent, Status: theme.Running},
		})
	}
	if !m.viewport.AtBottom() && len(m.messages) > 0 {
		pct := int(m.viewport.ScrollPercent() * 100)
		scrollInd := lipgloss.NewStyle().
			Foreground(lipgloss.Color("241")).
			Render(fmt.Sprintf("↑ %d%%", pct))
		pad := m.width - lipgloss.Width(statusContent) - lipgloss.Width(scrollInd) - 2
		if pad < 0 {
			pad = 0
		}
		statusContent += strings.Repeat(" ", pad) + scrollInd
	}

	// Render input lines: first gets the label, rest get padding.
	linePad := strings.Repeat(" ", prefixW)
	var inputRendered []string
	for i, line := range wrappedLines {
		rendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{Text: line})
		if i == 0 {
			inputRendered = append(inputRendered, prefix+rendered)
		} else {
			inputRendered = append(inputRendered, linePad+rendered)
		}
	}
	inputLine := sep + "\n" + strings.Join(inputRendered, "\n")

	// Compose final output.
	if acView != "" {
		return body + "\n" + acView + "\n" + statusContent + "\n" + inputLine
	}
	return body + "\n" + statusContent + "\n" + inputLine
}

// RenderHeader returns the chat header for the app to compose.
func (m *Model) RenderHeader() string {
	ctx := atoms.DefaultContext(m.width)

	agent := m.agentName
	if agent == "" {
		agent = "no agent"
	}

	badges := []atoms.BadgeData{
		{
			Label:   "agent: " + agent,
			Style:   theme.Style{Category: theme.CatAgent},
			Variant: atoms.BadgeOutline,
		},
	}

	if m.ExchangeCount > 0 {
		badges = append(badges, atoms.BadgeData{
			Label:   fmt.Sprintf("%d exchanges", m.ExchangeCount),
			Style:   theme.Style{Hierarchy: theme.Tertiary},
			Variant: atoms.BadgeOutline,
		})
	}

	if m.IsBranch {
		badges = append(badges, atoms.BadgeData{
			Label:   "branch",
			Style:   theme.Style{Category: theme.CatAgent},
			Variant: atoms.BadgeOutline,
		})
	}

	return molecules.Header(ctx, molecules.HeaderData{
		Title:  "CHAT",
		Badges: badges,
	})
}

func renderMessage(msg Message, width int) string {
	// Raw messages are pre-rendered — display as-is.
	if msg.Raw {
		return msg.RawContent
	}

	ctx := atoms.DefaultContext(width)

	switch msg.Role {
	case RoleUser:
		return molecules.MessageBlock(ctx, molecules.MessageBlockData{
			Role:    atoms.RoleUser,
			Content: msg.Content(),
		})

	case RoleAssistant:
		return renderAssistantMessage(ctx, msg, width)

	case RoleSystem:
		return molecules.MessageBlock(ctx, molecules.MessageBlockData{
			Role:    atoms.RoleSystem,
			Content: msg.Content(),
		})
	}
	return ""
}

func renderAssistantMessage(ctx atoms.RenderContext, msg Message, width int) string {
	badge := atoms.Badge(ctx, atoms.BadgeData{
		Label:   "assistant",
		Style:   theme.Style{Category: theme.CatAgent},
		Variant: atoms.BadgeFilled,
	})

	contentWidth := width - 4
	if contentWidth < 20 {
		contentWidth = 20
	}

	var sections []string
	sections = append(sections, badge)

	for _, part := range msg.Parts {
		rendered := renderPart(ctx, part, contentWidth)
		if rendered != "" {
			lines := strings.Split(rendered, "\n")
			indented := "  " + strings.Join(lines, "\n  ")
			sections = append(sections, indented)
		}
	}

	if len(sections) == 1 {
		return badge
	}

	return strings.Join(sections, "\n")
}

func renderPart(ctx atoms.RenderContext, part MessagePart, contentWidth int) string {
	switch part.Type {
	case PartText:
		if part.Content == "" {
			return ""
		}
		return ui.RenderMarkdown(part.Content, contentWidth)

	case PartThinking:
		if part.Content == "" {
			return ""
		}
		summary := part.Content
		if idx := strings.IndexByte(summary, '\n'); idx > 0 {
			summary = summary[:idx]
		}
		if len(summary) > 60 {
			summary = summary[:57] + "..."
		}
		return atoms.TextBlock(ctx, atoms.TextBlockData{
			Text:  "thinking: " + summary,
			Style: theme.Style{Hierarchy: theme.Tertiary},
		})

	case PartToolCall:
		return renderToolCallPart(ctx, part)

	case PartError:
		return molecules.ErrorBlock(ctx, molecules.ErrorBlockData{
			Message: part.Content,
		})
	}
	return ""
}

func renderToolCallPart(ctx atoms.RenderContext, part MessagePart) string {
	tc := part.ToolCall
	if tc == nil {
		return ""
	}

	// Map chat ToolCallState to molecules ToolCallState
	var state molecules.ToolCallState
	switch tc.State {
	case ToolCallStatePending:
		state = molecules.ToolCallPending
	case ToolCallStateRunning:
		state = molecules.ToolCallRunning
	case ToolCallStateComplete:
		state = molecules.ToolCallSuccess
	case ToolCallStateError:
		state = molecules.ToolCallError
	}

	args := formatArgs(tc.Arguments)

	result := tc.Result
	if tc.Error != "" {
		result = tc.Error
	}

	return molecules.ToolCallBlock(ctx, molecules.ToolCallBlockData{
		ToolName: tc.Name,
		State:    state,
		Args:     args,
		Result:   result,
	})
}
