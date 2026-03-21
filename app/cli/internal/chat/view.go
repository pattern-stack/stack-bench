package chat

import (
	"fmt"
	"strings"

	"charm.land/lipgloss/v2"

	"github.com/dugshub/stack-bench/app/cli/internal/ui"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
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
	left := " " + ui.Bold.Render("CHAT")

	// Build right-side metadata
	var meta []string
	meta = append(meta, ui.Dim.Render("agent: ")+ui.Accent.Render(agent))
	if m.ExchangeCount > 0 {
		meta = append(meta, ui.Dim.Render(fmt.Sprintf("%d exchanges", m.ExchangeCount)))
	}
	if m.IsBranch {
		meta = append(meta, ui.Accent.Render("[branch]"))
	}
	right := strings.Join(meta, ui.Dim.Render("  "))

	fill := m.width - lipgloss.Width(left) - lipgloss.Width(right)
	if fill < 0 {
		fill = 0
	}
	line := left + strings.Repeat(" ", fill) + right
	sep := ui.Dim.Render(strings.Repeat("─", m.width))
	return line + "\n" + sep
}

func (m *Model) renderMessages(maxH int) string {
	if len(m.messages) == 0 {
		empty := ui.Dim.Render("  No messages yet. Type below to start a conversation.")
		pad := maxH - 1
		if pad < 0 {
			pad = 0
		}
		return empty + strings.Repeat("\n", pad)
	}

	var rendered []string
	for _, msg := range m.messages {
		rendered = append(rendered, renderMessage(msg, m.width))
	}

	if m.streaming {
		rendered = append(rendered, ui.Accent.Render("  ..."))
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

func renderMessage(msg Message, width int) string {
	t := theme.Active()
	switch msg.Role {
	case RoleUser:
		return fmt.Sprintf(" %s %s", ui.Dim.Render("you:"), ui.Fg.Render(msg.Content))
	case RoleAssistant:
		prefix := ui.Accent.Render("sb:")
		contentWidth := width - 4
		if contentWidth < 20 {
			contentWidth = 20
		}
		rendered := ui.RenderMarkdown(msg.Content, contentWidth)
		lines := strings.Split(rendered, "\n")
		if len(lines) > 1 {
			indent := strings.Repeat(" ", lipgloss.Width("  "+prefix+" "))
			for i := 1; i < len(lines); i++ {
				lines[i] = indent + lines[i]
			}
		}
		return fmt.Sprintf("  %s %s", prefix, strings.Join(lines, "\n"))
	case RoleSystem:
		sysStyle := lipgloss.NewStyle().Foreground(t.Categories[theme.CatSystem])
		return fmt.Sprintf("  %s %s", sysStyle.Render("sys:"), sysStyle.Render(msg.Content))
	}
	return ""
}

func (m *Model) renderPrompt() string {
	sep := ui.Dim.Render(strings.Repeat("─", m.width))
	cursor := m.input + "_"
	prompt := fmt.Sprintf(" %s %s", ui.Dim.Render("you:"), ui.Fg.Render(cursor))
	return sep + "\n" + prompt
}
