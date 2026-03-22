package chat

import (
	"context"
	"strings"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/stack-bench/app/cli/internal/api"
	"github.com/dugshub/stack-bench/app/cli/internal/command"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/autocomplete"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
)

// Role is an alias for atoms.Role, the canonical role type in the component system.
type Role = atoms.Role

// Role constants re-exported from atoms for backward compatibility within the chat package.
const (
	RoleUser      = atoms.RoleUser
	RoleAssistant = atoms.RoleAssistant
	RoleSystem    = atoms.RoleSystem
)

// Message is a single chat message.
type Message struct {
	Role    Role
	Content string
}

// ResponseMsg is sent by the backend streaming response tea.Cmd.
type ResponseMsg struct {
	Chunk api.StreamChunk
}

// Model holds the state for the chat view.
type Model struct {
	messages       []Message
	input          string
	width, height  int
	conversationID string
	agentName      string
	client         api.Client
	streaming      bool
	streamCh       <-chan api.StreamChunk
	registry       *command.Registry
	autocomplete   autocomplete.Model
	ExchangeCount  int
	IsBranch       bool
}

// New creates a fresh chat model.
func New(client api.Client, agentName string, registry *command.Registry) Model {
	return Model{
		client:       client,
		agentName:    agentName,
		registry:     registry,
		autocomplete: autocomplete.New(registry),
	}
}

// SetSize updates the viewport dimensions.
func (m *Model) SetSize(w, h int) {
	m.width = w
	m.height = h
	m.autocomplete.SetWidth(w)
}

// SetConversationID sets the conversation identifier.
func (m *Model) SetConversationID(id string) {
	m.conversationID = id
}

// GetConversationID returns the current conversation identifier.
func (m *Model) GetConversationID() string {
	return m.conversationID
}

// IsInputEmpty reports whether the user input buffer is empty.
func (m *Model) IsInputEmpty() bool {
	return m.input == ""
}

// ClearInput resets the user input buffer.
func (m *Model) ClearInput() {
	m.input = ""
	m.autocomplete.Deactivate()
}

// AppendMessage adds a message to the chat history.
func (m *Model) AppendMessage(msg Message) {
	m.messages = append(m.messages, msg)
}

// Update handles key input and streaming response messages.
func (m *Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyPressMsg:
		return m.handleKey(msg)
	case ResponseMsg:
		return m.handleResponse(msg)
	case command.ClearMsg:
		m.messages = nil
		return *m, nil
	case command.ShowHelpMsg:
		m.showHelp(msg.Commands)
		return *m, nil
	}
	return *m, nil
}

func (m *Model) handleKey(msg tea.KeyPressMsg) (Model, tea.Cmd) {
	if m.streaming {
		return *m, nil
	}

	// Autocomplete is active — delegate navigation
	if m.autocomplete.IsActive() {
		switch msg.String() {
		case "esc":
			m.autocomplete.Deactivate()
			return *m, nil
		case "enter", "tab":
			if sel := m.autocomplete.Selected(); sel != nil {
				m.input = "/" + sel.Name + " "
				m.autocomplete.Deactivate()
				return *m, nil
			}
		case "backspace":
			m.input = deleteChar(m.input)
			if m.input == "" || m.input == "/" {
				m.autocomplete.Deactivate()
			} else {
				m.autocomplete.UpdateQuery(strings.TrimPrefix(m.input, "/"))
			}
			return *m, nil
		case "alt+backspace", "ctrl+w":
			m.input = deleteWord(m.input)
			if !strings.HasPrefix(m.input, "/") || m.input == "" {
				m.autocomplete.Deactivate()
			} else {
				m.autocomplete.UpdateQuery(strings.TrimPrefix(m.input, "/"))
			}
			return *m, nil
		case "super+backspace", "ctrl+u":
			m.input = ""
			m.autocomplete.Deactivate()
			return *m, nil
		default:
			// Typing refines the filter
			if msg.Text != "" {
				m.input += msg.Text
				m.autocomplete.UpdateQuery(strings.TrimPrefix(m.input, "/"))
				return *m, nil
			}
			// Up/down navigation
			m.autocomplete.Update(msg)
			return *m, nil
		}
	}

	switch msg.String() {
	case "backspace":
		m.input = deleteChar(m.input)
	case "alt+backspace", "ctrl+w":
		m.input = deleteWord(m.input)
	case "super+backspace", "ctrl+u":
		m.input = deleteLine(m.input)
	case "enter":
		return m.submit()
	default:
		if msg.Text != "" {
			m.input += msg.Text
			// Activate autocomplete when "/" is typed as first char
			if m.input == "/" {
				m.autocomplete.Activate("")
			}
		}
	}

	return *m, nil
}

func (m *Model) submit() (Model, tea.Cmd) {
	text := strings.TrimSpace(m.input)
	if text == "" {
		return *m, nil
	}

	m.input = ""
	m.autocomplete.Deactivate()

	// Handle slash commands
	if strings.HasPrefix(text, "/") {
		result := command.Parse(text)
		def := m.registry.Lookup(result.Command)
		if def == nil {
			m.messages = append(m.messages, Message{
				Role:    RoleSystem,
				Content: "Unknown command: " + text + ". Type /help for available commands.",
			})
			return *m, nil
		}
		if def.Handler != nil {
			return *m, def.Handler(result)
		}
		return *m, nil
	}

	// Regular message
	m.messages = append(m.messages, Message{Role: RoleUser, Content: text})
	m.streaming = true

	client := m.client
	convID := m.conversationID
	ch, err := client.SendMessage(context.Background(), convID, text)
	if err != nil {
		m.streaming = false
		m.messages = append(m.messages, Message{
			Role:    RoleAssistant,
			Content: "Error: " + err.Error(),
		})
		return *m, nil
	}
	m.streamCh = ch
	return *m, readStream(ch)
}

func (m *Model) handleResponse(msg ResponseMsg) (Model, tea.Cmd) {
	chunk := msg.Chunk

	if chunk.Error != nil {
		m.streaming = false
		m.streamCh = nil
		m.messages = append(m.messages, Message{
			Role:    RoleAssistant,
			Content: "Error: " + chunk.Error.Error(),
		})
		return *m, nil
	}

	if chunk.Content != "" {
		if len(m.messages) > 0 && m.messages[len(m.messages)-1].Role == RoleAssistant {
			m.messages[len(m.messages)-1].Content += chunk.Content
		} else {
			m.messages = append(m.messages, Message{Role: RoleAssistant, Content: chunk.Content})
		}
	}

	if chunk.Done {
		m.streaming = false
		m.streamCh = nil
		return *m, nil
	}

	return *m, readStream(m.streamCh)
}

func (m *Model) showHelp(commands []command.Def) {
	var lines []string
	lines = append(lines, "Available commands:")
	for _, cmd := range commands {
		aliases := ""
		if len(cmd.Aliases) > 0 {
			aliases = " (" + strings.Join(prefixAll(cmd.Aliases, "/"), ", ") + ")"
		}
		lines = append(lines, "  /"+cmd.Name+aliases+" — "+cmd.Description)
	}
	m.messages = append(m.messages, Message{
		Role:    RoleSystem,
		Content: strings.Join(lines, "\n"),
	})
}

func prefixAll(strs []string, prefix string) []string {
	result := make([]string, len(strs))
	for i, s := range strs {
		result[i] = prefix + s
	}
	return result
}

func readStream(ch <-chan api.StreamChunk) tea.Cmd {
	return func() tea.Msg {
		chunk, ok := <-ch
		if !ok {
			return ResponseMsg{Chunk: api.StreamChunk{Done: true}}
		}
		return ResponseMsg{Chunk: chunk}
	}
}
