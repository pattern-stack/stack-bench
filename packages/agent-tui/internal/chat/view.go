package chat

import (
	"fmt"
	"strings"

	"charm.land/lipgloss/v2"

	"github.com/dugshub/agent-tui/internal/ui"
	"github.com/dugshub/agent-tui/internal/ui/components/atoms"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// View renders the full chat view to fill the given dimensions.
func (m *Model) View() string {
	if m.width < 20 || m.height < 4 {
		return ""
	}

	header := m.renderHeader()
	prompt := m.renderPrompt()

	headerH := lipgloss.Height(header)
	promptH := lipgloss.Height(prompt)

	// Reserve space for autocomplete overlay if active
	acView := m.autocomplete.View()
	acH := 0
	if acView != "" {
		acH = lipgloss.Height(acView)
	}

	bodyH := m.height - headerH - promptH - acH
	if bodyH < 1 {
		bodyH = 1
	}

	body := m.renderMessages(bodyH)

	result := header + "\n" + body + "\n"
	if acView != "" {
		result += acView + "\n"
	}
	result += prompt

	return result
}

func (m *Model) renderHeader() string {
	agent := m.agentName
	if agent == "" {
		agent = "no agent"
	}
	left := " " + theme.Bold().Render("CHAT")

	// Build right-side metadata
	ctx := atoms.DefaultContext(m.width)
	var meta []string
	meta = append(meta, theme.Dim().Render("agent: ")+theme.Resolve(theme.Style{Category: theme.CatAgent}).Render(agent))
	if !ctx.Compact() {
		if m.ExchangeCount > 0 {
			meta = append(meta, theme.Dim().Render(fmt.Sprintf("%d exchanges", m.ExchangeCount)))
		}
		if m.IsBranch {
			meta = append(meta, theme.Resolve(theme.Style{Category: theme.CatAgent}).Render("[branch]"))
		}
	}
	right := strings.Join(meta, theme.Dim().Render("  "))

	fill := m.width - lipgloss.Width(left) - lipgloss.Width(right)
	if fill < 0 {
		fill = 0
	}
	line := left + strings.Repeat(" ", fill) + right
	sep := theme.Dim().Render(strings.Repeat("─", m.width))
	return line + "\n" + sep
}

func (m *Model) renderMessages(maxH int) string {
	if len(m.messages) == 0 {
		empty := theme.Dim().Render("  No messages yet. Type below to start a conversation.")
		pad := maxH - 1
		if pad < 0 {
			pad = 0
		}
		return empty + strings.Repeat("\n", pad)
	}

	var rendered []string
	for _, msg := range m.messages {
		rendered = append(rendered, m.renderMessage(msg, m.width))
	}

	if m.streaming {
		rendered = append(rendered, theme.Resolve(theme.Style{Category: theme.CatAgent}).Render("  ..."))
	}

	lineHeights := make([]int, len(rendered))
	for i, r := range rendered {
		lineHeights[i] = lipgloss.Height(r)
	}

	start := len(rendered)
	remaining := maxH
	for start > 0 && remaining > 0 {
		start--
		remaining -= lineHeights[start]
	}
	if remaining < 0 {
		start++
	}
	visible := rendered[start:]

	visibleLines := 0
	for _, r := range visible {
		visibleLines += lipgloss.Height(r)
	}
	padN := maxH - visibleLines
	var lines []string
	for i := 0; i < padN; i++ {
		lines = append(lines, "")
	}
	lines = append(lines, visible...)

	return strings.Join(lines, "\n")
}

func (m *Model) renderMessage(msg Message, width int) string {
	switch msg.Role {
	case RoleUser:
		return renderUserMessage(msg, width)
	case RoleAssistant:
		return m.renderAssistantMessage(msg, width)
	case RoleSystem:
		return renderSystemMessage(msg, width)
	}
	return ""
}

func renderUserMessage(msg Message, width int) string {
	return fmt.Sprintf(" %s %s", theme.Dim().Render("you:"), theme.Fg().Render(msg.Content()))
}

func renderSystemMessage(msg Message, width int) string {
	t := theme.Active()
	sysStyle := lipgloss.NewStyle().Foreground(t.Categories[theme.CatSystem])
	return fmt.Sprintf("  %s %s", sysStyle.Render("sys:"), sysStyle.Render(msg.Content()))
}

func (m *Model) renderAssistantMessage(msg Message, width int) string {
	label := m.assistantLabel
	if label == "" {
		label = "ai:"
	}
	prefix := theme.Resolve(theme.Style{Category: theme.CatAgent}).Render(label)
	contentWidth := width - 4
	if contentWidth < 20 {
		contentWidth = 20
	}

	var sections []string
	for _, part := range msg.Parts {
		sections = append(sections, renderPart(part, contentWidth))
	}

	// If no parts (legacy message with only Raw), fall back to markdown render
	if len(sections) == 0 && msg.Raw != "" {
		sections = append(sections, ui.RenderMarkdown(msg.Raw, contentWidth))
	}

	rendered := strings.Join(sections, "\n")
	lines := strings.Split(rendered, "\n")
	if len(lines) > 1 {
		indent := strings.Repeat(" ", lipgloss.Width("  "+prefix+" "))
		for i := 1; i < len(lines); i++ {
			lines[i] = indent + lines[i]
		}
	}
	return fmt.Sprintf("  %s %s", prefix, strings.Join(lines, "\n"))
}

func renderPart(part MessagePart, width int) string {
	switch p := part.(type) {
	case TextPart:
		return ui.RenderMarkdown(p.Content, width)
	case ThinkingPart:
		return renderThinkingPart(p, width)
	case ToolCallPart:
		return renderToolCallPart(p, width)
	case ErrorPart:
		return theme.Resolve(theme.Style{Status: theme.Error}).Render("Error: " + p.Message)
	}
	return ""
}

func renderThinkingPart(p ThinkingPart, width int) string {
	if p.Content == "" {
		return ""
	}
	lines := strings.Split(p.Content, "\n")
	summary := lines[0]
	if len(summary) > 60 {
		summary = summary[:57] + "..."
	}
	return theme.Dim().Render("thinking: " + summary)
}

func renderToolCallPart(p ToolCallPart, width int) string {
	// Status indicator
	var status string
	switch p.State {
	case ToolCallRunning:
		status = theme.Resolve(theme.Style{Category: theme.CatAgent}).Render("running")
	case ToolCallComplete:
		status = theme.Resolve(theme.Style{Status: theme.Success}).Render("done")
	case ToolCallFailed:
		status = theme.Resolve(theme.Style{Status: theme.Error}).Render("failed")
	}

	ctx := atoms.DefaultContext(width)
	var header string
	if ctx.Compact() {
		header = theme.Dim().Render("tool: ") + theme.Fg().Render(p.Name) + "\n  " + status
	} else {
		header = theme.Dim().Render("tool: ") + theme.Fg().Render(p.Name) + "  " + status
	}

	if p.State == ToolCallRunning {
		return header
	}

	if p.Error != "" {
		return header + "\n" + theme.Resolve(theme.Style{Status: theme.Error}).Render(p.Error)
	}

	// Dispatch result rendering by DisplayType
	switch p.DisplayType {
	case DisplayDiff:
		return header + "\n" + renderCodeFallback(p.Result, width)
	case DisplayCode:
		return header + "\n" + renderCodeFallback(p.Result, width)
	case DisplayBash:
		return header + "\n" + renderCodeFallback(p.Result, width)
	default: // DisplayGeneric
		return header + "\n" + theme.Dim().Render(truncate(p.Result, 200))
	}
}

func renderCodeFallback(content string, width int) string {
	ctx := atoms.DefaultContext(width)
	return atoms.CodeBlock(ctx, atoms.CodeBlockData{Code: content})
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}

func (m *Model) renderPrompt() string {
	sep := theme.Dim().Render(strings.Repeat("─", m.width))
	cursor := m.input + "_"
	prompt := fmt.Sprintf(" %s %s", theme.Dim().Render("you:"), theme.Fg().Render(cursor))
	return sep + "\n" + prompt
}
