package chat

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/dugshub/stack-bench/cli/internal/ui"
)

// View renders the full chat view to fill the given dimensions.
func (m Model) View() string {
	if m.Width < 20 || m.Height < 4 {
		return ""
	}

	header := m.renderHeader()
	prompt := m.renderPrompt()

	headerH := lipgloss.Height(header)
	promptH := lipgloss.Height(prompt)
	bodyH := m.Height - headerH - promptH
	if bodyH < 1 {
		bodyH = 1
	}

	body := m.renderMessages(bodyH)

	return header + "\n" + body + "\n" + prompt
}

func (m Model) renderHeader() string {
	agent := m.AgentName
	if agent == "" {
		agent = "no agent"
	}
	left := " " + ui.Bold.Render("CHAT")
	right := ui.Dim.Render("agent: ") + ui.Accent.Render(agent)
	fill := ui.MaxI(0, m.Width-lipgloss.Width(left)-lipgloss.Width(right))
	line := left + strings.Repeat(" ", fill) + right
	sep := ui.Dim.Render(strings.Repeat("─", m.Width))
	return line + "\n" + sep
}

func (m Model) renderMessages(maxH int) string {
	if len(m.Messages) == 0 {
		empty := ui.Dim.Render("  No messages yet. Type below to start a conversation.")
		pad := maxH - 1
		if pad < 0 {
			pad = 0
		}
		return empty + strings.Repeat("\n", pad)
	}

	// Render each message as one or more lines
	var rendered []string
	for _, msg := range m.Messages {
		rendered = append(rendered, renderMessage(msg))
	}

	if m.Streaming {
		rendered = append(rendered, ui.Accent.Render("  ..."))
	}

	// Calculate visual line counts for scroll offset
	totalLines := 0
	lineHeights := make([]int, len(rendered))
	for i, r := range rendered {
		h := lipgloss.Height(r)
		lineHeights[i] = h
		totalLines += h
	}

	// Show the tail that fits by counting visual lines
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

	// Pad to fill height
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

func (m Model) renderPrompt() string {
	sep := ui.Dim.Render(strings.Repeat("─", m.Width))
	cursor := m.Input + "_"
	prompt := fmt.Sprintf(" %s %s", ui.Dim.Render("you:"), ui.Fg.Render(cursor))
	return sep + "\n" + prompt
}
