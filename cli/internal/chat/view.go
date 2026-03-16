package chat

import (
	"fmt"
	"strings"

	"charm.land/lipgloss/v2"

	"github.com/dugshub/stack-bench/cli/internal/ui"
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
	bodyH := m.height - headerH - promptH
	if bodyH < 1 {
		bodyH = 1
	}

	body := m.renderMessages(bodyH)

	return header + "\n" + body + "\n" + prompt
}

func (m *Model) renderHeader() string {
	agent := m.agentName
	if agent == "" {
		agent = "no agent"
	}
	left := " " + ui.Bold.Render("CHAT")
	right := ui.Dim.Render("agent: ") + ui.Accent.Render(agent)
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
		rendered = append(rendered, renderMessage(msg))
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

func renderMessage(msg Message) string {
	switch msg.Role {
	case RoleUser:
		return fmt.Sprintf(" %s %s", ui.Dim.Render("you:"), ui.Fg.Render(msg.Content))
	case RoleAssistant:
		return fmt.Sprintf("  %s %s", ui.Accent.Render("sb:"), ui.Fg.Render(msg.Content))
	}
	return ""
}

func (m *Model) renderPrompt() string {
	sep := ui.Dim.Render(strings.Repeat("─", m.width))
	cursor := m.input + "_"
	prompt := fmt.Sprintf(" %s %s", ui.Dim.Render("you:"), ui.Fg.Render(cursor))
	return sep + "\n" + prompt
}
