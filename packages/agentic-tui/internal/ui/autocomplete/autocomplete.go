package autocomplete

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"

	"github.com/dugshub/agentic-tui/internal/command"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

const maxVisible = 6

// Model is an autocomplete dropdown for slash commands.
type Model struct {
	registry    *command.Registry
	suggestions []command.Def
	cursor      int
	query       string
	active      bool
	width       int
}

// New creates an autocomplete model backed by a command registry.
func New(registry *command.Registry) Model {
	return Model{registry: registry}
}

// SetWidth sets the available width for rendering.
func (m *Model) SetWidth(w int) {
	m.width = w
}

// Activate shows the autocomplete dropdown, filtering by query.
func (m *Model) Activate(query string) {
	m.active = true
	m.query = query
	m.cursor = 0
	m.filter()
}

// Deactivate hides the dropdown.
func (m *Model) Deactivate() {
	m.active = false
	m.suggestions = nil
	m.query = ""
	m.cursor = 0
}

// IsActive reports whether the dropdown is visible.
func (m *Model) IsActive() bool {
	return m.active
}

// UpdateQuery refines the suggestion list as the user types.
func (m *Model) UpdateQuery(query string) {
	m.query = query
	m.cursor = 0
	m.filter()
}

// Selected returns the currently highlighted command, or nil.
func (m *Model) Selected() *command.Def {
	if !m.active || len(m.suggestions) == 0 {
		return nil
	}
	def := m.suggestions[m.cursor]
	return &def
}

// Update handles navigation keys while the dropdown is active.
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

// View renders the dropdown above the input line.
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

		// Pad name to fixed width for alignment
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

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
