package chat

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"

	"github.com/dugshub/agentic-tui/internal/sse"
	"github.com/dugshub/agentic-tui/internal/ui/components/atoms"
	"github.com/dugshub/agentic-tui/internal/ui/components/molecules"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

// PickerAction describes what the user chose to do with a conversation.
type PickerAction int

const (
	ActionNew      PickerAction = iota // Start a new conversation
	ActionContinue                     // Continue an existing conversation
	ActionBranch                       // Branch from an existing conversation
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
	case "b":
		// Branch only works on existing conversations
		if m.cursor > 0 && m.cursor <= len(m.conversations) {
			conv := m.conversations[m.cursor-1]
			return m, func() tea.Msg {
				return ConversationSelectedMsg{
					Action:         ActionBranch,
					ConversationID: conv.ID,
				}
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

	ctx := atoms.DefaultContext(m.width)
	// Use a zero-width context for inline text rendering (no width padding)
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	var lines []string

	header := molecules.Header(ctx, molecules.HeaderData{
		Title: "CONVERSATIONS",
		Badges: []atoms.BadgeData{
			{
				Label:   m.agentName,
				Style:   theme.Style{Category: theme.CatAgent},
				Variant: atoms.BadgeOutline,
			},
		},
	})
	lines = append(lines, header)
	lines = append(lines, "")

	if m.loadErr != nil {
		errBlock := molecules.ErrorBlock(ctx, molecules.ErrorBlockData{
			Message: fmt.Sprintf("%v", m.loadErr),
		})
		lines = append(lines, "  "+errBlock)
	} else if m.loading {
		lines = append(lines, "  "+atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  "Loading conversations...",
			Style: theme.Style{Hierarchy: theme.Tertiary},
		}))
	} else {
		// "New conversation" option
		newCursor := "  "
		newLabel := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text: "+ New conversation",
		})
		if m.cursor == 0 {
			newCursor = atoms.Icon(inlineCtx, atoms.IconCursor, theme.Style{Category: theme.CatAgent}) + " "
			newLabel = atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text:  "+ New conversation",
				Style: theme.Style{Category: theme.CatAgent},
			})
		}
		lines = append(lines, fmt.Sprintf("  %s%s", newCursor, newLabel))
		lines = append(lines, "")

		if len(m.conversations) > 0 {
			lines = append(lines, "  "+atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text:  "Past conversations:",
				Style: theme.Style{Hierarchy: theme.Tertiary},
			}))
			lines = append(lines, "")

			for i, conv := range m.conversations {
				idx := i + 1 // offset by 1 for the "new" option
				cursor := "  "
				if m.cursor == idx {
					cursor = atoms.Icon(inlineCtx, atoms.IconCursor, theme.Style{Category: theme.CatAgent}) + " "
				}

				// Format: state, exchange count, time
				label := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
					Text: conv.AgentName,
				})
				if m.cursor == idx {
					label = atoms.TextBlock(inlineCtx, atoms.TextBlockData{
						Text:  conv.AgentName,
						Style: theme.Style{Category: theme.CatAgent},
					})
				}

				meta := fmt.Sprintf("%s  %d exchanges  %s",
					conv.State,
					conv.ExchangeCount,
					conv.UpdatedAt.Format("Jan 2 15:04"),
				)

				metaText := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
					Text:  meta,
					Style: theme.Style{Hierarchy: theme.Tertiary},
				})

				branch := ""
				if conv.BranchedFromID != nil {
					branch = " " + atoms.Badge(inlineCtx, atoms.BadgeData{
						Label:   "branch",
						Style:   theme.Style{Category: theme.CatAgent},
						Variant: atoms.BadgeOutline,
					})
				}

				lines = append(lines,
					fmt.Sprintf("  %s%s  %s%s", cursor, label, metaText, branch),
				)
			}
		} else {
			lines = append(lines, "  "+atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text:  "No past conversations.",
				Style: theme.Style{Hierarchy: theme.Tertiary},
			}))
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
