package autocomplete

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"

	"github.com/dugshub/agent-tui/internal/command"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

const maxVisible = 6

type Model struct {
	registry    *command.Registry
	suggestions []command.Def
	cursor      int
	query       string
	active      bool
	width       int
}

func New(registry *command.Registry) Model {
	return Model{registry: registry}
}

func (m *Model) SetWidth(w int)       { m.width = w }
func (m *Model) IsActive() bool       { return m.active }

func (m *Model) Activate(query string) {
	m.active = true
	m.query = query
	m.cursor = 0
	m.filter()
}

func (m *Model) Deactivate() {
	m.active = false
	m.suggestions = nil
	m.query = ""
	m.cursor = 0
}

func (m *Model) UpdateQuery(query string) {
	m.query = query
	m.cursor = 0
	m.filter()
}

func (m *Model) Selected() *command.Def {
	if !m.active || len(m.suggestions) == 0 {
		return nil
	}
	def := m.suggestions[m.cursor]
	return &def
}

func (m *Model) Update(msg tea.Msg) tea.Cmd {
	keyMsg, ok := msg.(tea.KeyPressMsg)
	if !ok {
		return nil
	}
	switch keyMsg.String() {
	case "up", "shift+tab":
		if m.cursor > 0 {
			m.cursor--
		} else {
			m.cursor = len(m.suggestions) - 1
		}
	case "down", "tab":
		if m.cursor < len(m.suggestions)-1 {
			m.cursor++
		} else {
			m.cursor = 0
		}
	}
	return nil
}

func (m *Model) View() string {
	if !m.active || len(m.suggestions) == 0 {
		return ""
	}

	t := theme.Active()
	nameStyle := lipgloss.NewStyle().Foreground(t.Categories[theme.CatAgent])
	descStyle := lipgloss.NewStyle().Foreground(t.DimColor)
	selectedBg := lipgloss.NewStyle().
		Background(t.Categories[theme.CatAgent]).
		Foreground(t.Background).
		Bold(true)
	selectedDesc := lipgloss.NewStyle().
		Background(t.Categories[theme.CatAgent]).
		Foreground(t.Background)

	visible := m.suggestions
	if len(visible) > maxVisible {
		visible = visible[:maxVisible]
	}

	var lines []string
	for i, def := range visible {
		name := "/" + def.Name
		desc := def.Description
		nameW := 12
		padded := name + strings.Repeat(" ", max(0, nameW-len(name)))

		if i == m.cursor {
			line := fmt.Sprintf(" %s %s ", selectedBg.Render(padded), selectedDesc.Render(desc))
			lines = append(lines, line)
		} else {
			line := fmt.Sprintf(" %s %s", nameStyle.Render(padded), descStyle.Render(desc))
			lines = append(lines, line)
		}
	}

	border := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.DimColor).
		Width(min(m.width-4, 50))

	return border.Render(strings.Join(lines, "\n"))
}

func (m *Model) filter() {
	if m.query == "" {
		m.suggestions = m.registry.List("")
	} else {
		m.suggestions = m.registry.Suggest(m.query, maxVisible)
	}
}
