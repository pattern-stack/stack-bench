package chat

import (
	"context"
	"strings"

	"charm.land/bubbles/v2/key"
	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/stack-bench/app/cli/internal/api"
	"github.com/dugshub/stack-bench/app/cli/internal/command"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/autocomplete"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
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
	viewport       viewport.Model
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
		Left:  key.NewBinding(), // disabled
		Right: key.NewBinding(), // disabled
	}
}

// New creates a fresh chat model.
func New(client api.Client, agentName string, registry *command.Registry) Model {
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

// Chat chrome heights (status line = 1 line, input = sep + text).
const (
	statusLineHeight = 1 // streaming/scroll indicator (no separator)
	inputHeight      = 2 // separator + "you: _"
	chatChrome       = statusLineHeight + inputHeight + 2 // +2 newlines between sections
)

// SetSize updates the viewport dimensions.
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

	var rendered []string
	for _, msg := range m.messages {
		rendered = append(rendered, renderMessage(msg, m.width))
	}

	m.viewport.SetContent(strings.Join(rendered, "\n"))

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
			m.rebuildViewportContent()
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
	m.rebuildViewportContent()

	client := m.client
	convID := m.conversationID
	ch, err := client.SendMessage(context.Background(), convID, text)
	if err != nil {
		m.streaming = false
		m.messages = append(m.messages, Message{
			Role:    RoleAssistant,
			Content: "Error: " + err.Error(),
		})
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
		m.messages = append(m.messages, Message{
			Role:    RoleAssistant,
			Content: "Error: " + chunk.Error.Error(),
		})
		m.rebuildViewportContent()
		return *m, nil
	}

	if chunk.Content != "" {
		if len(m.messages) > 0 && m.messages[len(m.messages)-1].Role == RoleAssistant {
			m.messages[len(m.messages)-1].Content += chunk.Content
		} else {
			m.messages = append(m.messages, Message{Role: RoleAssistant, Content: chunk.Content})
		}
		m.rebuildViewportContent()
	}

	if chunk.Done {
		m.streaming = false
		m.streamCh = nil
		m.rebuildViewportContent()
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
	m.rebuildViewportContent()
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
