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

	// Adjust viewport height for autocomplete overlay if active
	acView := m.autocomplete.View()
	acH := 0
	if acView != "" {
		acH = lipgloss.Height(acView)
	}

	// Temporarily adjust viewport height if autocomplete is visible
	if acH > 0 {
		origH := m.viewport.Height()
		m.viewport.SetHeight(origH - acH)
		defer m.viewport.SetHeight(origH)
	}

	body := m.viewport.View()

	// Show a scroll indicator when the user has scrolled up
	if !m.viewport.AtBottom() && len(m.messages) > 0 {
		pct := int(m.viewport.ScrollPercent() * 100)
		indicator := fmt.Sprintf(" ↑ %d%% ", pct)
		// Right-align the indicator on the last line of the body
		pad := m.width - lipgloss.Width(indicator)
		if pad < 0 {
			pad = 0
		}
		body += "\n" + strings.Repeat(" ", pad) + lipgloss.NewStyle().
			Foreground(lipgloss.Color("241")).
			Render(indicator)
	}

	prompt := m.renderPrompt()

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
