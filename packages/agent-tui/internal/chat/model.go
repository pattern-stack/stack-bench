package chat

import (
	"context"
	"strings"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/agent-tui/internal/command"
	"github.com/dugshub/agent-tui/internal/sse"
	"github.com/dugshub/agent-tui/internal/ui/autocomplete"
)

// Role identifies the sender of a chat message.
type Role int

const (
	RoleUser Role = iota
	RoleAssistant
	RoleSystem
)

// PartType identifies the kind of content within a message.
type PartType int

const (
	PartText     PartType = iota
	PartThinking
	PartToolCall
	PartError
)

// ToolCallState tracks the lifecycle of a tool invocation.
type ToolCallState int

const (
	ToolCallRunning  ToolCallState = iota
	ToolCallComplete
	ToolCallFailed
)

// DisplayType controls how a tool result is rendered.
type DisplayType string

const (
	DisplayDiff    DisplayType = "diff"
	DisplayCode    DisplayType = "code"
	DisplayBash    DisplayType = "bash"
	DisplayGeneric DisplayType = "generic"
)

// MessagePart is a sealed interface for message content parts.
type MessagePart interface {
	partType() PartType
}

type TextPart struct{ Content string }
func (TextPart) partType() PartType { return PartText }

type ThinkingPart struct{ Content string }
func (ThinkingPart) partType() PartType { return PartThinking }

type ToolCallPart struct {
	ID          string
	Name        string
	DisplayType DisplayType
	State       ToolCallState
	Input       string
	Result      string
	Error       string
}
func (ToolCallPart) partType() PartType { return PartToolCall }

type ErrorPart struct{ Message string }
func (ErrorPart) partType() PartType { return PartError }

// Message is a single chat message composed of parts.
type Message struct {
	Role  Role
	Parts []MessagePart
	Raw   string
}

func (m Message) Content() string {
	if m.Raw != "" {
		return m.Raw
	}
	var sb strings.Builder
	for _, p := range m.Parts {
		switch v := p.(type) {
		case TextPart:
			sb.WriteString(v.Content)
		case ErrorPart:
			sb.WriteString("Error: " + v.Message)
		}
	}
	return sb.String()
}

// ResponseMsg is sent by the backend streaming response tea.Cmd.
type ResponseMsg struct {
	Chunk sse.StreamChunk
}

// ClientInterface matches the internal client interface methods we need.
type ClientInterface interface {
	ListAgents(ctx context.Context) ([]sse.AgentSummary, error)
	SendMessage(ctx context.Context, conversationID string, content string) (<-chan sse.StreamChunk, error)
	CreateConversation(ctx context.Context, agentID string) (string, error)
	ListConversations(ctx context.Context, agentName string) ([]sse.Conversation, error)
	GetConversation(ctx context.Context, id string) (*sse.ConversationDetail, error)
}

// Model holds the state for the chat view.
type Model struct {
	messages       []Message
	input          string
	width, height  int
	conversationID string
	agentName      string
	assistantLabel string
	client         ClientInterface
	streaming      bool
	streamCh       <-chan sse.StreamChunk
	registry       *command.Registry
	autocomplete   autocomplete.Model
	ExchangeCount  int
	IsBranch       bool
}

// New creates a fresh chat model.
func New(client ClientInterface, agentName string, registry *command.Registry, assistantLabel string) Model {
	return Model{
		client:         client,
		agentName:      agentName,
		registry:       registry,
		assistantLabel: assistantLabel,
		autocomplete:   autocomplete.New(registry),
	}
}

func (m *Model) SetSize(w, h int) {
	m.width = w
	m.height = h
	m.autocomplete.SetWidth(w)
}

func (m *Model) SetConversationID(id string) { m.conversationID = id }
func (m *Model) GetConversationID() string    { return m.conversationID }
func (m *Model) IsInputEmpty() bool           { return m.input == "" }
func (m *Model) ClearInput() {
	m.input = ""
	m.autocomplete.Deactivate()
}
func (m *Model) AppendMessage(msg Message) { m.messages = append(m.messages, msg) }
func (m *Model) AssistantLabel() string     { return m.assistantLabel }

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
			if msg.Text != "" {
				m.input += msg.Text
				m.autocomplete.UpdateQuery(strings.TrimPrefix(m.input, "/"))
				return *m, nil
			}
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

	if strings.HasPrefix(text, "/") {
		result := command.Parse(text)
		def := m.registry.Lookup(result.Command)
		if def == nil {
			m.messages = append(m.messages, Message{
				Role: RoleSystem,
				Raw:  "Unknown command: " + text + ". Type /help for available commands.",
			})
			return *m, nil
		}
		if def.Handler != nil {
			return *m, def.Handler(result)
		}
		return *m, nil
	}

	m.messages = append(m.messages, Message{Role: RoleUser, Raw: text})
	m.streaming = true

	client := m.client
	convID := m.conversationID
	ch, err := client.SendMessage(context.Background(), convID, text)
	if err != nil {
		m.streaming = false
		m.appendPart(RoleAssistant, ErrorPart{Message: err.Error()})
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
		m.appendPart(RoleAssistant, ErrorPart{Message: chunk.Error.Error()})
		return *m, nil
	}

	switch chunk.Type {
	case sse.ChunkText:
		m.accumulateText(chunk.Content)
	case sse.ChunkThinking:
		m.accumulateThinking(chunk.Content)
	case sse.ChunkToolStart:
		m.startToolCall(chunk)
	case sse.ChunkToolEnd:
		m.endToolCall(chunk)
	}

	if chunk.Done {
		m.streaming = false
		m.streamCh = nil
		m.finalizeRaw()
		return *m, nil
	}
	return *m, readStream(m.streamCh)
}

func (m *Model) accumulateText(content string) {
	msg := m.ensureAssistantMessage()
	if len(msg.Parts) > 0 {
		if tp, ok := msg.Parts[len(msg.Parts)-1].(TextPart); ok {
			msg.Parts[len(msg.Parts)-1] = TextPart{Content: tp.Content + content}
			return
		}
	}
	msg.Parts = append(msg.Parts, TextPart{Content: content})
}

func (m *Model) accumulateThinking(content string) {
	msg := m.ensureAssistantMessage()
	if len(msg.Parts) > 0 {
		if tp, ok := msg.Parts[len(msg.Parts)-1].(ThinkingPart); ok {
			msg.Parts[len(msg.Parts)-1] = ThinkingPart{Content: tp.Content + content}
			return
		}
	}
	msg.Parts = append(msg.Parts, ThinkingPart{Content: content})
}

func (m *Model) startToolCall(chunk sse.StreamChunk) {
	msg := m.ensureAssistantMessage()
	msg.Parts = append(msg.Parts, ToolCallPart{
		ID:          chunk.ToolCallID,
		Name:        chunk.ToolName,
		DisplayType: DisplayType(chunk.DisplayType),
		State:       ToolCallRunning,
		Input:       chunk.ToolInput,
	})
}

func (m *Model) endToolCall(chunk sse.StreamChunk) {
	msg := m.currentAssistantMessage()
	if msg == nil {
		return
	}
	for i, p := range msg.Parts {
		if tc, ok := p.(ToolCallPart); ok && tc.ID == chunk.ToolCallID {
			tc.Result = chunk.Content
			tc.Error = chunk.ToolError
			if tc.Error != "" {
				tc.State = ToolCallFailed
			} else {
				tc.State = ToolCallComplete
			}
			msg.Parts[i] = tc
			return
		}
	}
}

func (m *Model) ensureAssistantMessage() *Message {
	if len(m.messages) == 0 || m.messages[len(m.messages)-1].Role != RoleAssistant {
		m.messages = append(m.messages, Message{Role: RoleAssistant})
	}
	return &m.messages[len(m.messages)-1]
}

func (m *Model) currentAssistantMessage() *Message {
	if len(m.messages) > 0 && m.messages[len(m.messages)-1].Role == RoleAssistant {
		return &m.messages[len(m.messages)-1]
	}
	return nil
}

func (m *Model) finalizeRaw() {
	msg := m.currentAssistantMessage()
	if msg == nil {
		return
	}
	var sb strings.Builder
	for _, p := range msg.Parts {
		if tp, ok := p.(TextPart); ok {
			sb.WriteString(tp.Content)
		}
	}
	msg.Raw = sb.String()
}

func (m *Model) appendPart(role Role, part MessagePart) {
	if len(m.messages) == 0 || m.messages[len(m.messages)-1].Role != role {
		m.messages = append(m.messages, Message{Role: role})
	}
	m.messages[len(m.messages)-1].Parts = append(m.messages[len(m.messages)-1].Parts, part)
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
		Role: RoleSystem,
		Raw:  strings.Join(lines, "\n"),
	})
}

func prefixAll(strs []string, prefix string) []string {
	result := make([]string, len(strs))
	for i, s := range strs {
		result[i] = prefix + s
	}
	return result
}

func readStream(ch <-chan sse.StreamChunk) tea.Cmd {
	return func() tea.Msg {
		chunk, ok := <-ch
		if !ok {
			return ResponseMsg{Chunk: sse.StreamChunk{Done: true}}
		}
		return ResponseMsg{Chunk: chunk}
	}
}
