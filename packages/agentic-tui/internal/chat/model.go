package chat

import (
	"context"
	"encoding/json"
	"strings"
	"time"

	"charm.land/bubbles/v2/key"
	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/agentic-tui/internal/command"
	"github.com/dugshub/agentic-tui/internal/types"
	"github.com/dugshub/agentic-tui/internal/ui/autocomplete"
	"github.com/dugshub/agentic-tui/internal/ui/components/atoms"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

// Role is an alias for atoms.Role, the canonical role type in the component system.
type Role = atoms.Role

// Role constants re-exported from atoms for backward compatibility within the chat package.
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
	StartedAt   time.Time // set when the tool call starts; drives spinner graduation
}

// MessagePart is one segment of a message (text, thinking, tool call, or error).
type MessagePart struct {
	Type     PartType
	Content  string
	ToolCall *ToolCallPart
	Complete bool
}

// Message is a single chat message with structured parts.
type Message struct {
	Role       Role
	Parts      []MessagePart
	Raw        bool   // when true, RawContent is pre-rendered — bypass parts
	RawContent string // only used when Raw is true
}

// Content returns the text content of the message.
// For raw messages, returns RawContent. For part-based messages,
// concatenates all part content.
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
	Chunk types.StreamChunk
}

// Model holds the state for the chat view.
type Model struct {
	messages       []Message
	input          string
	width, height  int
	conversationID string
	agentName      string
	client         types.Client
	streaming      bool
	streamCh       <-chan types.StreamChunk
	registry       *command.Registry
	autocomplete    autocomplete.Model
	viewport        viewport.Model
	toolSpinner     atoms.Spinner // SparseCenter for running tool calls
	thinkingSpinner atoms.Spinner // Star for active thinking
	spinnerActive   bool
	ExchangeCount   int
	IsBranch        bool
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
		Left:  key.NewBinding(), // disabled
		Right: key.NewBinding(), // disabled
	}
}

// New creates a fresh chat model.
func New(client types.Client, agentName string, registry *command.Registry) Model {
	vp := viewport.New()
	vp.SoftWrap = true
	vp.MouseWheelEnabled = true
	vp.KeyMap = chatScrollKeyMap()
	vp.FillHeight = true

	return Model{
		client:       client,
		agentName:    agentName,
		registry:     registry,
		autocomplete: autocomplete.New(registry),
		viewport:     vp,
	}
}

// Chat chrome heights (status line = 1 line, input = sep + at least one line).
const (
	statusLineHeight = 1 // streaming/scroll indicator (no separator)
	minInputHeight   = 2 // separator + at least one line of "you: _"
	chatChrome       = statusLineHeight + minInputHeight + 2 // +2 newlines between sections
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

// SaveScrollPosition returns the current YOffset for later restoration.
func (m *Model) SaveScrollPosition() int {
	return m.viewport.YOffset()
}

// GotoBottom scrolls to the bottom of the viewport.
func (m *Model) GotoBottom() {
	m.viewport.GotoBottom()
}

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

// rebuildViewportContent re-renders all messages into the viewport.
// It preserves scroll position when the user has scrolled up, and
// auto-scrolls to the bottom otherwise.
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

	spinners := spinnerSet{tool: m.toolSpinner, thinking: m.thinkingSpinner}
	var rendered []string
	for i, msg := range m.messages {
		isLast := i == len(m.messages)-1
		rendered = append(rendered, renderMessage(msg, m.width, spinners, isLast))
	}

	m.viewport.SetContent(strings.Join(rendered, "\n\n"))

	if wasAtBottom {
		m.viewport.GotoBottom()
	}
}

// SetInput pre-fills the input buffer (used by demo mode).
func (m *Model) SetInput(text string) {
	m.input = text
}

// Update handles key input and streaming response messages.
func (m *Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyPressMsg:
		return m.handleKey(msg)
	case tea.MouseWheelMsg:
		// Delegate mouse wheel events to the viewport for scrolling.
		var cmd tea.Cmd
		m.viewport, cmd = m.viewport.Update(msg)
		return *m, cmd
	case atoms.SpinnerTickMsg:
		if !m.spinnerActive {
			return *m, nil
		}
		var cmd tea.Cmd
		switch msg.ID {
		case m.toolSpinner.ID:
			m.toolSpinner, cmd = m.toolSpinner.Update(msg)
		case m.thinkingSpinner.ID:
			m.thinkingSpinner, cmd = m.thinkingSpinner.Update(msg)
		}
		m.rebuildViewportContent()
		return *m, cmd
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

// isScrollKey returns true if the key press should be handled by the viewport
// for scrolling rather than passed to the text input.
func isScrollKey(msg tea.KeyPressMsg) bool {
	switch msg.String() {
	case "pgup", "pgdown", "shift+up", "shift+down", "ctrl+u", "ctrl+d":
		return true
	}
	return false
}

func (m *Model) handleKey(msg tea.KeyPressMsg) (Model, tea.Cmd) {
	// Scroll keys go to the viewport even while streaming.
	// ctrl+u/ctrl+d are dual-purpose: they scroll when the input is empty
	// (or when streaming), but act as input editing keys otherwise.
	k := msg.String()
	isCtrlUD := k == "ctrl+u" || k == "ctrl+d"
	if isScrollKey(msg) {
		if !isCtrlUD || m.streaming || m.input == "" {
			var cmd tea.Cmd
			m.viewport, cmd = m.viewport.Update(msg)
			return *m, cmd
		}
	}

	if m.streaming {
		// Enter skips streaming — drain remaining chunks immediately
		if k == "enter" {
			m.skipStreaming()
			return *m, nil
		}
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
	case "shift+enter", "alt+enter", "ctrl+j":
		m.input += "\n"
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
	// Spin up both spinners — tool spinner (SparseCenter) for tool calls
	// and thinking spinner (Star) for active thinking. Both tick for the
	// duration of streaming; the view decides which one to show per part.
	m.toolSpinner = atoms.Spinner{
		ID:     1,
		Style:  theme.Style{Status: theme.Running},
		Frames: atoms.SpinnerSparseCenter,
	}
	m.thinkingSpinner = atoms.Spinner{
		ID:     2,
		Style:  theme.Style{Status: theme.Running},
		Frames: atoms.SpinnerStar,
	}
	m.spinnerActive = true
	return *m, tea.Batch(readStream(ch), m.toolSpinner.Init(), m.thinkingSpinner.Init())
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
	case types.ChunkText:
		if chunk.Content != "" {
			m.appendToLastPart(PartText, chunk.Content)
		}

	case types.ChunkThinking:
		if chunk.Content != "" {
			m.appendToLastPart(PartThinking, chunk.Content)
		}

	case types.ChunkToolStart:
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
				StartedAt:   time.Now(),
			},
		})

	case types.ChunkToolEnd:
		m.completeToolCall(chunk)

	case types.ChunkToolReject:
		m.ensureAssistantMessage()
		last := &m.messages[len(m.messages)-1]
		last.Parts = append(last.Parts, MessagePart{
			Type:     PartError,
			Content:  "Tool rejected: " + chunk.ToolName + ": " + chunk.Content,
			Complete: true,
		})

	case types.ChunkError:
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
		// Mark all parts complete
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
func (m *Model) completeToolCall(chunk types.StreamChunk) {
	if len(m.messages) == 0 {
		return
	}
	last := &m.messages[len(m.messages)-1]
	// Match by tool call ID
	for i := len(last.Parts) - 1; i >= 0; i-- {
		p := &last.Parts[i]
		if p.Type == PartToolCall && p.ToolCall != nil && p.ToolCall.ID == chunk.ToolCallID {
			m.fillToolCallResult(p, chunk)
			return
		}
	}
	// Fallback: match most recent running tool call
	for i := len(last.Parts) - 1; i >= 0; i-- {
		p := &last.Parts[i]
		if p.Type == PartToolCall && p.ToolCall != nil && p.ToolCall.State == ToolCallStateRunning {
			m.fillToolCallResult(p, chunk)
			return
		}
	}
}

func (m *Model) fillToolCallResult(p *MessagePart, chunk types.StreamChunk) {
	if chunk.ToolError != "" {
		p.ToolCall.State = ToolCallStateError
		p.ToolCall.Error = chunk.ToolError
	} else {
		p.ToolCall.State = ToolCallStateComplete
	}
	p.ToolCall.Result = chunk.Result
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
		case types.ChunkText:
			if chunk.Content != "" {
				m.appendToLastPart(PartText, chunk.Content)
			}
		case types.ChunkThinking:
			if chunk.Content != "" {
				m.appendToLastPart(PartThinking, chunk.Content)
			}
		case types.ChunkToolStart:
			m.ensureAssistantMessage()
			last := &m.messages[len(m.messages)-1]
			last.Parts = append(last.Parts, MessagePart{
				Type: PartToolCall,
				ToolCall: &ToolCallPart{
					ID: chunk.ToolCallID, Name: chunk.ToolName,
					DisplayType: chunk.DisplayType, Arguments: chunk.Arguments,
					State:     ToolCallStateRunning,
					StartedAt: time.Now(),
				},
			})
		case types.ChunkToolEnd:
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

func readStream(ch <-chan types.StreamChunk) tea.Cmd {
	return func() tea.Msg {
		chunk, ok := <-ch
		if !ok {
			return ResponseMsg{Chunk: types.StreamChunk{Done: true}}
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
