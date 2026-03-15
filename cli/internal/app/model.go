package app

import (
	"context"
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/dugshub/stack-bench/cli/internal/api"
	"github.com/dugshub/stack-bench/cli/internal/chat"
	"github.com/dugshub/stack-bench/cli/internal/ui"
)

// Phase represents the current phase of the app lifecycle.
type Phase int

const (
	PhaseSelectAgent Phase = iota
	PhaseChat
)

// AgentsLoadedMsg is sent when the agent list has been fetched.
type AgentsLoadedMsg struct {
	Agents []api.Agent
	Err    error
}

// ConversationCreatedMsg is sent when a conversation is ready.
type ConversationCreatedMsg struct {
	ConversationID string
	Err            error
}

// Model is the top-level Bubble Tea model.
type Model struct {
	width, height int
	phase         Phase
	client        api.Client

	// Agent selection
	agents      []api.Agent
	agentCursor int
	loadErr     error

	// Chat
	chat chat.Model
}

// New creates the initial app model.
func New(client api.Client) Model {
	return Model{
		width:  80,
		height: 24,
		phase:  PhaseSelectAgent,
		client: client,
	}
}

// Init starts the app by loading available agents.
func (m Model) Init() tea.Cmd {
	client := m.client
	return func() tea.Msg {
		agents, err := client.ListAgents(context.Background())
		return AgentsLoadedMsg{Agents: agents, Err: err}
	}
}

// Update handles all incoming messages.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.chat.SetSize(m.width, m.height-2) // reserve space for status bar
		return m, nil

	case tea.KeyMsg:
		if msg.String() == "ctrl+c" {
			return m, tea.Quit
		}

	case AgentsLoadedMsg:
		if msg.Err != nil {
			m.loadErr = msg.Err
			return m, nil
		}
		m.agents = msg.Agents
		return m, nil

	case ConversationCreatedMsg:
		if msg.Err != nil {
			m.loadErr = msg.Err
			return m, nil
		}
		m.chat.SetConversationID(msg.ConversationID)
		m.phase = PhaseChat
		return m, nil
	}

	switch m.phase {
	case PhaseSelectAgent:
		return m.updateAgentSelect(msg)
	case PhaseChat:
		return m.updateChat(msg)
	}

	return m, nil
}

func (m Model) updateAgentSelect(msg tea.Msg) (tea.Model, tea.Cmd) {
	keyMsg, ok := msg.(tea.KeyMsg)
	if !ok {
		return m, nil
	}

	switch keyMsg.String() {
	case "q":
		return m, tea.Quit
	case "j", "down":
		if m.agentCursor < len(m.agents)-1 {
			m.agentCursor++
		}
	case "k", "up":
		if m.agentCursor > 0 {
			m.agentCursor--
		}
	case "enter":
		if len(m.agents) > 0 {
			agent := m.agents[m.agentCursor]
			m.chat = chat.New(m.client, agent.Name)
			m.chat.SetSize(m.width, m.height-2)

			client := m.client
			agentID := agent.ID
			return m, func() tea.Msg {
				id, err := client.CreateConversation(context.Background(), agentID)
				return ConversationCreatedMsg{ConversationID: id, Err: err}
			}
		}
	}

	return m, nil
}

func (m Model) updateChat(msg tea.Msg) (tea.Model, tea.Cmd) {
	// Esc: if input has text, clear it first; if empty, go back to agent select
	if keyMsg, ok := msg.(tea.KeyMsg); ok {
		if keyMsg.String() == "esc" {
			if !m.chat.IsInputEmpty() {
				m.chat.ClearInput()
				return m, nil
			}
			m.phase = PhaseSelectAgent
			return m, nil
		}
	}

	newChat, cmd := m.chat.Update(msg)
	m.chat = newChat
	return m, cmd
}

// View renders the current view.
func (m Model) View() string {
	if m.width < 30 {
		return "resize terminal"
	}

	var body string
	switch m.phase {
	case PhaseSelectAgent:
		body = m.viewAgentSelect()
	case PhaseChat:
		body = m.chat.View()
	}

	status := m.renderStatus()
	return body + "\n" + status
}

func (m Model) viewAgentSelect() string {
	var lines []string

	title := ui.Bold.Render(" STACK BENCH")
	lines = append(lines, title)
	lines = append(lines, ui.Dim.Render(strings.Repeat("─", m.width)))
	lines = append(lines, "")

	if m.loadErr != nil {
		lines = append(lines, ui.Red.Render(fmt.Sprintf("  Error: %v", m.loadErr)))
		lines = append(lines, "")
		lines = append(lines, ui.Dim.Render("  Press q to quit."))
	} else if len(m.agents) == 0 {
		lines = append(lines, ui.Dim.Render("  Loading agents..."))
	} else {
		lines = append(lines, ui.Fg.Render("  Select an agent to start a conversation:"))
		lines = append(lines, "")

		for i, agent := range m.agents {
			cursor := "  "
			if i == m.agentCursor {
				cursor = ui.Accent.Render("> ")
			}

			name := ui.Fg.Render(agent.Name)
			if i == m.agentCursor {
				name = ui.Bold.Render(agent.Name)
			}

			role := ui.Dim.Render(agent.Role)
			lines = append(lines, fmt.Sprintf("  %s%s  %s", cursor, name, role))
		}
	}

	// Pad to fill available height
	bodyH := m.height - 2 // status bar
	for len(lines) < bodyH {
		lines = append(lines, "")
	}

	return lipgloss.NewStyle().Width(m.width).Height(bodyH).Render(
		strings.Join(lines, "\n"),
	)
}

func (m Model) renderStatus() string {
	var hint string
	switch m.phase {
	case PhaseSelectAgent:
		hint = "j/k: navigate  enter: select  q: quit"
	case PhaseChat:
		hint = "enter: send  esc: back to agents  ctrl+c: quit"
	}
	sep := ui.Dim.Render(strings.Repeat("─", m.width))
	return sep + "\n" + ui.Dim.Render(" "+hint)
}
