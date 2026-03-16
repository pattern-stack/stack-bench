package chat

import (
	"context"
	"strings"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/stack-bench/cli/internal/api"
)

// Role identifies the sender of a chat message.
type Role int

const (
	RoleUser Role = iota
	RoleAssistant
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
	streaming      bool                  // true while receiving a streamed response
	streamCh       <-chan api.StreamChunk // active stream channel during response
}

// New creates a fresh chat model.
func New(client api.Client, agentName string) Model {
	return Model{
		client:    client,
		agentName: agentName,
	}
}

// SetSize updates the viewport dimensions.
func (m *Model) SetSize(w, h int) {
	m.width = w
	m.height = h
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
}

// Update handles key input and streaming response messages.
func (m *Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyPressMsg:
		return m.handleKey(msg)
	case ResponseMsg:
		return m.handleResponse(msg)
	}
	return *m, nil
}

func (m *Model) handleKey(msg tea.KeyPressMsg) (Model, tea.Cmd) {
	if m.streaming {
		return *m, nil
	}

	switch msg.String() {
	case "backspace":
		if len(m.input) > 0 {
			m.input = m.input[:len(m.input)-1]
		}
	case "enter":
		return m.submit()
	default:
		if msg.Text != "" {
			m.input += msg.Text
		}
	}

	return *m, nil
}

func (m *Model) submit() (Model, tea.Cmd) {
	text := strings.TrimSpace(m.input)
	if text == "" {
		return *m, nil
	}

	m.messages = append(m.messages, Message{Role: RoleUser, Content: text})
	m.input = ""
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

func readStream(ch <-chan api.StreamChunk) tea.Cmd {
	return func() tea.Msg {
		chunk, ok := <-ch
		if !ok {
			return ResponseMsg{Chunk: api.StreamChunk{Done: true}}
		}
		return ResponseMsg{Chunk: chunk}
	}
}
