package chat

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"

	"github.com/dugshub/agent-tui/internal/sse"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// PickerAction describes what the user chose to do with a conversation.
type PickerAction int

const (
	ActionNew      PickerAction = iota // Start a new conversation
	ActionContinue                     // Continue an existing conversation
)

// ConversationSelectedMsg is sent when the user picks a conversation.
type ConversationSelectedMsg struct {
	Action         PickerAction
	ConversationID string // empty for ActionNew
}

// ConversationsLoadedMsg is sent when the conversation list has been fetched.
type ConversationsLoadedMsg struct {
	Conversations []sse.Conversation
	Err           error
}

// PickerModel is a Bubble Tea model for choosing a conversation.
type PickerModel struct {
	conversations []sse.Conversation
	cursor        int
	width, height int
	agentName     string
	loading       bool
	loadErr       error
}

// NewPicker creates a picker for the given agent.
func NewPicker(agentName string) PickerModel {
	return PickerModel{
		agentName: agentName,
		loading:   true,
	}
}

// SetSize updates the viewport dimensions.
func (m *PickerModel) SetSize(w, h int) {
	m.width = w
	m.height = h
}

// Update handles key input and data messages.
func (m PickerModel) Update(msg tea.Msg) (PickerModel, tea.Cmd) {
	switch msg := msg.(type) {
	case ConversationsLoadedMsg:
		m.loading = false
		if msg.Err != nil {
			m.loadErr = msg.Err
			return m, nil
		}
		m.conversations = msg.Conversations
		return m, nil

	case tea.KeyPressMsg:
		return m.handleKey(msg)
	}
	return m, nil
}

func (m PickerModel) handleKey(msg tea.KeyPressMsg) (PickerModel, tea.Cmd) {
	// Total items: 1 (new) + len(conversations)
	total := 1 + len(m.conversations)

	switch msg.String() {
	case "j", "down":
		if m.cursor < total-1 {
			m.cursor++
		}
	case "k", "up":
		if m.cursor > 0 {
			m.cursor--
		}
	case "enter":
		if m.cursor == 0 {
			return m, func() tea.Msg {
				return ConversationSelectedMsg{Action: ActionNew}
			}
		}
		conv := m.conversations[m.cursor-1]
		return m, func() tea.Msg {
			return ConversationSelectedMsg{
				Action:         ActionContinue,
				ConversationID: conv.ID,
			}
		}
	}

	return m, nil
}

// View renders the picker.
func (m PickerModel) View() string {
	if m.width < 20 || m.height < 4 {
		return ""
	}

	var lines []string

	header := " " + theme.Bold().Render("CONVERSATIONS") +
		theme.Dim().Render(" — ") +
		theme.Resolve(theme.Style{Category: theme.CatAgent}).Render(m.agentName)
	lines = append(lines, header)
	lines = append(lines, theme.Dim().Render(strings.Repeat("─", m.width)))
	lines = append(lines, "")

	if m.loadErr != nil {
		lines = append(lines, theme.Resolve(theme.Style{Status: theme.Error}).Render(fmt.Sprintf("  Error: %v", m.loadErr)))
	} else if m.loading {
		lines = append(lines, theme.Dim().Render("  Loading conversations..."))
	} else {
		// "New conversation" option
		newCursor := "  "
		newLabel := theme.Fg().Render("+ New conversation")
		if m.cursor == 0 {
			newCursor = theme.Resolve(theme.Style{Category: theme.CatAgent}).Render("> ")
			newLabel = theme.Bold().Render("+ New conversation")
		}
		lines = append(lines, fmt.Sprintf("  %s%s", newCursor, newLabel))
		lines = append(lines, "")

		if len(m.conversations) > 0 {
			lines = append(lines, theme.Dim().Render("  Past conversations:"))
			lines = append(lines, "")

			for i, conv := range m.conversations {
				idx := i + 1 // offset by 1 for the "new" option
				cursor := "  "
				if m.cursor == idx {
					cursor = theme.Resolve(theme.Style{Category: theme.CatAgent}).Render("> ")
				}

				// Format: state, exchange count, time
				label := conv.AgentID
				if m.cursor == idx {
					label = theme.Bold().Render(label)
				} else {
					label = theme.Fg().Render(label)
				}

				meta := fmt.Sprintf("%s  %d exchanges  %s",
					conv.State,
					conv.ExchangeCount,
					conv.UpdatedAt.Format("Jan 2 15:04"),
				)

				lines = append(lines,
					fmt.Sprintf("  %s%s  %s", cursor, label, theme.Dim().Render(meta)),
				)
			}
		} else {
			lines = append(lines, theme.Dim().Render("  No past conversations."))
		}
	}

	// Pad to fill height
	for len(lines) < m.height {
		lines = append(lines, "")
	}

	return lipgloss.NewStyle().Width(m.width).Height(m.height).Render(
		strings.Join(lines, "\n"),
	)
}
