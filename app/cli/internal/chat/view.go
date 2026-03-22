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

func (m *Model) renderMessages(maxH int) string {
	ctx := atoms.DefaultContext(m.width)

	if len(m.messages) == 0 {
		empty := atoms.TextBlock(ctx, atoms.TextBlockData{
			Text:  "  No messages yet. Type below to start a conversation.",
			Style: theme.Style{Hierarchy: theme.Tertiary},
		})
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
		rendered = append(rendered, atoms.TextBlock(ctx, atoms.TextBlockData{
			Text:  "  ...",
			Style: theme.Style{Category: theme.CatAgent, Status: theme.Running},
		}))
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
	ctx := atoms.DefaultContext(width)

	switch msg.Role {
	case RoleUser:
		return molecules.MessageBlock(ctx, molecules.MessageBlockData{
			Role:    atoms.RoleUser,
			Content: msg.Content,
		})

	case RoleAssistant:
		// Assistant messages use markdown rendering which MessageBlock doesn't cover yet.
		// Use the role badge pattern from atoms, then render markdown content with indentation.
		badge := atoms.Badge(ctx, atoms.BadgeData{
			Label:   "assistant",
			Style:   theme.Style{Category: theme.CatAgent},
			Variant: atoms.BadgeFilled,
		})
		contentWidth := width - 4
		if contentWidth < 20 {
			contentWidth = 20
		}
		rendered := ui.RenderMarkdown(msg.Content, contentWidth)
		lines := strings.Split(rendered, "\n")
		indented := "  " + strings.Join(lines, "\n  ")
		return badge + "\n" + indented

	case RoleSystem:
		return molecules.MessageBlock(ctx, molecules.MessageBlockData{
			Role:    atoms.RoleSystem,
			Content: msg.Content,
		})
	}
	return ""
}

func (m *Model) renderPrompt() string {
	ctx := atoms.DefaultContext(m.width)

	sep := atoms.Separator(ctx)
	cursor := m.input + "_"

	label := atoms.TextBlock(atoms.RenderContext{Width: 0, Theme: ctx.Theme}, atoms.TextBlockData{
		Text:  "you:",
		Style: theme.Style{Hierarchy: theme.Tertiary},
	})
	input := atoms.TextBlock(atoms.RenderContext{Width: 0, Theme: ctx.Theme}, atoms.TextBlockData{
		Text:  cursor,
		Style: theme.Style{},
	})

	return sep + "\n" + " " + label + " " + input
}
