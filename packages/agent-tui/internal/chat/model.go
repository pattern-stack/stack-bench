package chat

import (
	"context"
	"encoding/json"
	"strings"

	"charm.land/bubbles/v2/key"
	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/agent-tui/internal/command"
	"github.com/dugshub/agent-tui/internal/sse"
	"github.com/dugshub/agent-tui/internal/ui/autocomplete"
	"github.com/dugshub/agent-tui/internal/ui/components/atoms"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// Role is an alias for atoms.Role, the canonical role type in the component system.
type Role = atoms.Role

// Role constants re-exported from atoms for use within the chat package.
const (
	RoleUser      = atoms.RoleUser
	RoleAssistant = atoms.RoleAssistant
	RoleSystem    = atoms.RoleSystem
)

// PartType identifies the kind of message part.
type PartType string

const (
	PartText     PartType = "text"
	PartThinking PartType = "thinking"
	PartToolCall PartType = "tool_call"
	PartError    PartType = "error"
)

// ToolCallState tracks the lifecycle of a tool call.
type ToolCallState string

const (
	ToolCallStatePending  ToolCallState = "pending"
	ToolCallStateRunning  ToolCallState = "running"
	ToolCallStateComplete ToolCallState = "complete"
	ToolCallStateError    ToolCallState = "error"
)

// ToolCallPart holds structured data for a tool call part.
type ToolCallPart struct {
	ID          string
	Name        string
	DisplayType string
	Arguments   map[string]any
	State       ToolCallState
	Result      string
	Error       string
	DurationMs  int
}

// MessagePart is one segment of a message (text, thinking, tool call, or error).
type MessagePart struct {
	Type     PartType
	Content  string
	ToolCall *ToolCallPart
	Complete bool
}

// Message is a single chat message with structured parts.
// When Raw is true, RawContent is pre-rendered output (used by gallery mode).
type Message struct {
	Role       Role
	Parts      []MessagePart
	Raw        bool
	RawContent string
}

// Content returns the text content of the message.
// For raw messages, returns RawContent. For part-based messages,
// concatenates the content of all parts.
func (m Message) Content() string {
	if m.Raw {
		return m.RawContent
	}
	var buf strings.Builder
	for _, p := range m.Parts {
		buf.WriteString(p.Content)
	}
	return buf.String()
}

// TextMessage creates a simple single-text-part message.
func TextMessage(role Role, content string) Message {
	return Message{
		Role:  role,
		Parts: []MessagePart{{Type: PartText, Content: content, Complete: true}},
	}
}

// ResponseMsg is sent by the backend streaming response tea.Cmd.
type ResponseMsg struct {
	Chunk sse.StreamChunk
}

// Model holds the state for the chat view.
type Model struct {
	messages       []Message
	input          string
	width, height  int
	conversationID string
	agentName      string
	assistantLabel string
	client         sse.Client
	streaming      bool
	streamCh       <-chan sse.StreamChunk
	registry       *command.Registry
	autocomplete   autocomplete.Model
	viewport       viewport.Model
	spinner        atoms.Spinner
	spinnerActive  bool
	ExchangeCount  int
	IsBranch       bool
}

// chatScrollKeyMap returns a KeyMap that avoids conflicts with text input.
// Only special keys (pgup/pgdown, shift+arrows) are bound; letter keys
// like j/k/f/b/d/u that the default keymap uses are omitted so they can
// be typed normally.
func chatScrollKeyMap() viewport.KeyMap {
	return viewport.KeyMap{
		PageDown: key.NewBinding(
			key.WithKeys("pgdown"),
			key.WithHelp("pgdn", "page down"),
		),
		PageUp: key.NewBinding(
			key.WithKeys("pgup"),
			key.WithHelp("pgup", "page up"),
		),
		HalfPageUp: key.NewBinding(
			key.WithKeys("ctrl+u"),
			key.WithHelp("ctrl+u", "½ page up"),
		),
		HalfPageDown: key.NewBinding(
			key.WithKeys("ctrl+d"),
			key.WithHelp("ctrl+d", "½ page down"),
		),
		Up: key.NewBinding(
			key.WithKeys("shift+up"),
			key.WithHelp("shift+↑", "scroll up"),
		),
		Down: key.NewBinding(
			key.WithKeys("shift+down"),
			key.WithHelp("shift+↓", "scroll down"),
		),
		Left:  key.NewBinding(),
		Right: key.NewBinding(),
	}
}

// New creates a fresh chat model.
func New(client sse.Client, agentName string, registry *command.Registry, assistantLabel string) Model {
	vp := viewport.New()
	vp.SoftWrap = true
	vp.MouseWheelEnabled = true
	vp.KeyMap = chatScrollKeyMap()
	vp.FillHeight = true

	return Model{
		client:         client,
		agentName:      agentName,
		registry:       registry,
		assistantLabel: assistantLabel,
		autocomplete:   autocomplete.New(registry),
		viewport:       vp,
	}
}

// Chat chrome heights (status line + input separator + at least one input line).
const (
	statusLineHeight = 1
	minInputHeight   = 2
	chatChrome       = statusLineHeight + minInputHeight + 2
)

// SetSize updates the viewport dimensions and re-renders content at the new width.
func (m *Model) SetSize(w, h int) {
	m.width = w
	m.height = h
	m.autocomplete.SetWidth(w)
	m.viewport.SetWidth(w)
	vpHeight := h - chatChrome
	if vpHeight < 1 {
		vpHeight = 1
	}
	m.viewport.SetHeight(vpHeight)
	m.rebuildViewportContent()
}

func (m *Model) SetConversationID(id string) { m.conversationID = id }
func (m *Model) GetConversationID() string    { return m.conversationID }
func (m *Model) IsInputEmpty() bool           { return m.input == "" }
func (m *Model) AssistantLabel() string       { return m.assistantLabel }

func (m *Model) ClearInput() {
	m.input = ""
	m.autocomplete.Deactivate()
}

// SaveScrollPosition returns the current YOffset for later restoration.
func (m *Model) SaveScrollPosition() int { return m.viewport.YOffset() }

// GotoBottom scrolls to the bottom of the viewport.
func (m *Model) GotoBottom() { m.viewport.GotoBottom() }

// RestoreScrollPosition sets the YOffset, clamping to valid range.
func (m *Model) RestoreScrollPosition(offset int) {
	max := m.viewport.TotalLineCount() - m.viewport.VisibleLineCount()
	if max < 0 {
		max = 0
	}
	if offset > max {
		offset = max
	}
	m.viewport.SetYOffset(offset)
}

// ClearMessages removes all messages from the chat history.
func (m *Model) ClearMessages() {
	m.messages = nil
	m.rebuildViewportContent()
}

// AppendMessage adds a message to the chat history.
func (m *Model) AppendMessage(msg Message) {
	m.messages = append(m.messages, msg)
	m.rebuildViewportContent()
}

// SetInput pre-fills the input buffer (used by demo mode).
func (m *Model) SetInput(text string) {
	m.input = text
}

// rebuildViewportContent re-renders all messages into the viewport.
// Preserves scroll position when the user has scrolled up; auto-scrolls
// to the bottom otherwise.
func (m *Model) rebuildViewportContent() {
	wasAtBottom := m.viewport.AtBottom()

	if len(m.messages) == 0 {
		ctx := atoms.DefaultContext(m.width)
		empty := atoms.TextBlock(ctx, atoms.TextBlockData{
			Text:  "  No messages yet. Type below to start a conversation.",
			Style: theme.Style{Hierarchy: theme.Tertiary},
		})
		m.viewport.SetContent(empty)
		return
	}

	var rendered []string
	for _, msg := range m.messages {
		rendered = append(rendered, renderMessage(msg, m.width, m.spinner, m.assistantLabel))
	}

	m.viewport.SetContent(strings.Join(rendered, "\n"))

	if wasAtBottom {
		m.viewport.GotoBottom()
	}
}

// Update handles key input and streaming response messages.
func (m *Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyPressMsg:
		return m.handleKey(msg)
	case tea.MouseWheelMsg:
		var cmd tea.Cmd
		m.viewport, cmd = m.viewport.Update(msg)
		return *m, cmd
	case atoms.SpinnerTickMsg:
		if m.spinnerActive {
			var cmd tea.Cmd
			m.spinner, cmd = m.spinner.Update(msg)
			m.rebuildViewportContent()
			return *m, cmd
		}
		return *m, nil
	case ResponseMsg:
		return m.handleResponse(msg)
	case command.ClearMsg:
		m.messages = nil
		m.rebuildViewportContent()
		return *m, nil
	case command.ShowHelpMsg:
		m.showHelp(msg.Commands)
		return *m, nil
	}
	return *m, nil
}

// isScrollKey returns true if the key press should be handled by the viewport.
func isScrollKey(msg tea.KeyPressMsg) bool {
	switch msg.String() {
	case "pgup", "pgdown", "shift+up", "shift+down", "ctrl+u", "ctrl+d":
		return true
	}
	return false
}

func (m *Model) handleKey(msg tea.KeyPressMsg) (Model, tea.Cmd) {
	k := msg.String()
	// ctrl+u/ctrl+d are dual-purpose: scroll when input is empty or streaming,
	// otherwise act as input editing keys.
	isCtrlUD := k == "ctrl+u" || k == "ctrl+d"
	if isScrollKey(msg) {
		if !isCtrlUD || m.streaming || m.input == "" {
			var cmd tea.Cmd
			m.viewport, cmd = m.viewport.Update(msg)
			return *m, cmd
		}
	}

	if m.streaming {
		// Enter skips streaming — drain remaining chunks immediately.
		if k == "enter" {
			m.skipStreaming()
			return *m, nil
		}
		return *m, nil
	}

	// Autocomplete is active — delegate navigation.
	if m.autocomplete.IsActive() {
		switch k {
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

	switch k {
	case "backspace":
		m.input = deleteChar(m.input)
	case "alt+backspace", "ctrl+w":
		m.input = deleteWord(m.input)
	case "super+backspace", "ctrl+u":
		m.input = deleteLine(m.input)
	case "shift+enter", "alt+enter", "ctrl+j":
		m.input += "\n"
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

	// Slash commands
	if strings.HasPrefix(text, "/") {
		result := command.Parse(text)
		def := m.registry.Lookup(result.Command)
		if def == nil {
			m.messages = append(m.messages, TextMessage(RoleSystem,
				"Unknown command: "+text+". Type /help for available commands."))
			m.rebuildViewportContent()
			return *m, nil
		}
		if def.Handler != nil {
			return *m, def.Handler(result)
		}
		return *m, nil
	}

	// Regular message
	m.messages = append(m.messages, TextMessage(RoleUser, text))
	m.streaming = true
	m.rebuildViewportContent()

	client := m.client
	convID := m.conversationID
	ch, err := client.SendMessage(context.Background(), convID, text)
	if err != nil {
		m.streaming = false
		m.messages = append(m.messages, TextMessage(RoleAssistant, "Error: "+err.Error()))
		m.rebuildViewportContent()
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
		m.messages = append(m.messages, TextMessage(RoleAssistant, "Error: "+chunk.Error.Error()))
		m.rebuildViewportContent()
		return *m, nil
	}

	switch chunk.Type {
	case sse.ChunkText:
		if chunk.Content != "" {
			m.appendToLastPart(PartText, chunk.Content)
		}

	case sse.ChunkThinking:
		if chunk.Content != "" {
			m.appendToLastPart(PartThinking, chunk.Content)
		}

	case sse.ChunkToolStart:
		m.ensureAssistantMessage()
		last := &m.messages[len(m.messages)-1]
		last.Parts = append(last.Parts, MessagePart{
			Type: PartToolCall,
			ToolCall: &ToolCallPart{
				ID:          chunk.ToolCallID,
				Name:        chunk.ToolName,
				DisplayType: chunk.DisplayType,
				Arguments:   chunk.Arguments,
				State:       ToolCallStateRunning,
			},
		})
		if !m.spinnerActive {
			m.spinner = atoms.NewSpinner(1, theme.Style{Status: theme.Running})
			m.spinnerActive = true
			m.rebuildViewportContent()
			return *m, tea.Batch(readStream(m.streamCh), m.spinner.Init())
		}

	case sse.ChunkToolEnd:
		m.completeToolCall(chunk)
		m.spinnerActive = false

	case sse.ChunkToolReject:
		m.ensureAssistantMessage()
		last := &m.messages[len(m.messages)-1]
		last.Parts = append(last.Parts, MessagePart{
			Type:     PartError,
			Content:  "Tool rejected: " + chunk.ToolName + ": " + chunk.Content,
			Complete: true,
		})

	case sse.ChunkError:
		m.ensureAssistantMessage()
		last := &m.messages[len(m.messages)-1]
		last.Parts = append(last.Parts, MessagePart{
			Type:     PartError,
			Content:  chunk.Content,
			Complete: true,
		})
	}

	if chunk.Done {
		m.streaming = false
		m.streamCh = nil
		m.spinnerActive = false
		// Mark all parts of the last assistant message complete.
		if len(m.messages) > 0 {
			last := &m.messages[len(m.messages)-1]
			for i := range last.Parts {
				last.Parts[i].Complete = true
			}
		}
		m.rebuildViewportContent()
		return *m, nil
	}

	m.rebuildViewportContent()
	return *m, readStream(m.streamCh)
}

// ensureAssistantMessage makes sure the last message is an assistant message.
func (m *Model) ensureAssistantMessage() {
	if len(m.messages) == 0 || m.messages[len(m.messages)-1].Role != RoleAssistant {
		m.messages = append(m.messages, Message{Role: RoleAssistant})
	}
}

// appendToLastPart appends content to the last part of the given type,
// or creates a new part if the last part is a different type.
func (m *Model) appendToLastPart(partType PartType, content string) {
	m.ensureAssistantMessage()
	last := &m.messages[len(m.messages)-1]
	if len(last.Parts) > 0 {
		p := &last.Parts[len(last.Parts)-1]
		if p.Type == partType && !p.Complete {
			p.Content += content
			return
		}
	}
	last.Parts = append(last.Parts, MessagePart{Type: partType, Content: content})
}

// completeToolCall finds the matching tool call part and fills in the result.
func (m *Model) completeToolCall(chunk sse.StreamChunk) {
	if len(m.messages) == 0 {
		return
	}
	last := &m.messages[len(m.messages)-1]
	// Match by tool call ID first
	for i := len(last.Parts) - 1; i >= 0; i-- {
		p := &last.Parts[i]
		if p.Type == PartToolCall && p.ToolCall != nil && p.ToolCall.ID == chunk.ToolCallID {
			m.fillToolCallResult(p, chunk)
			return
		}
	}
	// Fallback: most recent running tool call
	for i := len(last.Parts) - 1; i >= 0; i-- {
		p := &last.Parts[i]
		if p.Type == PartToolCall && p.ToolCall != nil && p.ToolCall.State == ToolCallStateRunning {
			m.fillToolCallResult(p, chunk)
			return
		}
	}
}

func (m *Model) fillToolCallResult(p *MessagePart, chunk sse.StreamChunk) {
	if chunk.ToolError != "" {
		p.ToolCall.State = ToolCallStateError
		p.ToolCall.Error = chunk.ToolError
	} else {
		p.ToolCall.State = ToolCallStateComplete
	}
	// Prefer explicit Result, fall back to Content for older backends.
	if chunk.Result != "" {
		p.ToolCall.Result = chunk.Result
	} else {
		p.ToolCall.Result = chunk.Content
	}
	p.ToolCall.DurationMs = chunk.DurationMs
	p.Complete = true
}

// skipStreaming drains the stream channel and completes the response immediately.
func (m *Model) skipStreaming() {
	if m.streamCh == nil {
		return
	}
	for chunk := range m.streamCh {
		switch chunk.Type {
		case sse.ChunkText:
			if chunk.Content != "" {
				m.appendToLastPart(PartText, chunk.Content)
			}
		case sse.ChunkThinking:
			if chunk.Content != "" {
				m.appendToLastPart(PartThinking, chunk.Content)
			}
		case sse.ChunkToolStart:
			m.ensureAssistantMessage()
			last := &m.messages[len(m.messages)-1]
			last.Parts = append(last.Parts, MessagePart{
				Type: PartToolCall,
				ToolCall: &ToolCallPart{
					ID: chunk.ToolCallID, Name: chunk.ToolName,
					DisplayType: chunk.DisplayType, Arguments: chunk.Arguments,
					State: ToolCallStateRunning,
				},
			})
		case sse.ChunkToolEnd:
			m.completeToolCall(chunk)
		default:
			if chunk.Content != "" {
				m.appendToLastPart(PartText, chunk.Content)
			}
		}
		if chunk.Done {
			break
		}
	}
	m.streaming = false
	m.streamCh = nil
	m.spinnerActive = false
	m.rebuildViewportContent()
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
	m.messages = append(m.messages, TextMessage(RoleSystem, strings.Join(lines, "\n")))
	m.rebuildViewportContent()
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

// formatArgs converts a map of arguments to a compact display string.
func formatArgs(args map[string]any) string {
	if len(args) == 0 {
		return ""
	}
	b, err := json.Marshal(args)
	if err != nil {
		return ""
	}
	s := string(b)
	if len(s) > 80 {
		s = s[:77] + "..."
	}
	return s
}
