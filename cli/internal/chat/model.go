package chat

import (
	"context"
	"strings"

	tea "github.com/charmbracelet/bubbletea"

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
	Messages       []Message
	Input          string
	Width, Height  int
	Scroll         int
	ConversationID string
	AgentName      string
	Client         api.Client
	Streaming      bool // true while receiving a streamed response
}

// New creates a fresh chat model.
func New(client api.Client, agentName string) Model {
	return Model{
		Client:    client,
		AgentName: agentName,
	}
}

// SetSize updates the viewport dimensions.
func (m *Model) SetSize(w, h int) {
	m.Width = w
	m.Height = h
}

// Update handles key input and streaming response messages.
func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		return m.handleKey(msg)
	case ResponseMsg:
		return m.handleResponse(msg)
	}
	return m, nil
}

func (m Model) handleKey(msg tea.KeyMsg) (Model, tea.Cmd) {
	if m.Streaming {
		// While streaming, ignore most input
		return m, nil
	}

	switch msg.Type {
	case tea.KeyBackspace:
		if len(m.Input) > 0 {
			m.Input = m.Input[:len(m.Input)-1]
		}
	case tea.KeyEnter:
		return m.submit()
	case tea.KeyRunes:
		m.Input += string(msg.Runes)
	}

	// Vim-style scroll when input is empty
	if m.Input == "" {
		switch msg.String() {
		case "j", "down":
			m.Scroll++
		case "k", "up":
			if m.Scroll > 0 {
				m.Scroll--
			}
		}
	}

	return m, nil
}

func (m Model) submit() (Model, tea.Cmd) {
	text := strings.TrimSpace(m.Input)
	if text == "" {
		return m, nil
	}

	m.Messages = append(m.Messages, Message{Role: RoleUser, Content: text})
	m.Input = ""
	m.Streaming = true

	// Return a command that sends the message to the backend
	client := m.Client
	convID := m.ConversationID
	return m, func() tea.Msg {
		ch, err := client.SendMessage(context.Background(), convID, text)
		if err != nil {
			return ResponseMsg{Chunk: api.StreamChunk{
				Content: "Error: " + err.Error(),
				Done:    true,
				Error:   err,
			}}
		}
		// Read the first chunk (the tea runtime will call Update for each)
		chunk, ok := <-ch
		if !ok {
			return ResponseMsg{Chunk: api.StreamChunk{Done: true}}
		}
		return ResponseMsg{Chunk: chunk}
	}
}

func (m Model) handleResponse(msg ResponseMsg) (Model, tea.Cmd) {
	chunk := msg.Chunk

	if chunk.Content != "" {
		// Append to the last assistant message, or create a new one
		if len(m.Messages) > 0 && m.Messages[len(m.Messages)-1].Role == RoleAssistant {
			m.Messages[len(m.Messages)-1].Content += chunk.Content
		} else {
			m.Messages = append(m.Messages, Message{Role: RoleAssistant, Content: chunk.Content})
		}
	}

	if chunk.Done {
		m.Streaming = false
		return m, nil
	}

	// Continue reading from the stream (for future real streaming)
	return m, nil
}
