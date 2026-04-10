package app

import (
	"context"
	"fmt"
	"strings"
	"time"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"

	"github.com/dugshub/agentic-tui/internal/chat"
	"github.com/dugshub/agentic-tui/internal/command"
	"github.com/dugshub/agentic-tui/internal/service"
	"github.com/dugshub/agentic-tui/internal/types"
	"github.com/dugshub/agentic-tui/internal/ui/components/atoms"
	"github.com/dugshub/agentic-tui/internal/ui/components/molecules"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

// Phase represents the current phase of the app lifecycle.
type Phase int

const (
	PhaseSelectAgent Phase = iota
	PhaseChat
)

// AgentsLoadedMsg is sent when the agent list has been fetched.
type AgentsLoadedMsg struct {
	Agents []types.AgentSummary
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
	client        types.Client
	manager       *service.ServiceManager

	// Agent selection
	agents      []types.AgentSummary
	agentCursor int
	loadErr     error

	// Chat
	chat     chat.Model
	registry *command.Registry

	// Runtime health
	healthStatuses map[string]service.ServiceStatus
	statusSpinner  atoms.Spinner // Heartbeat animation in the status bar

	// Demo mode
	demo       bool
	demoRunner *DemoRunner

	// Gallery mode
	gallery       bool
	galleryLoaded bool
}

// New creates the initial app model.
func New(client types.Client, mgr *service.ServiceManager) Model {
	reg := command.DefaultRegistry()
	return Model{
		width:    80,
		height:   24,
		phase:    PhaseSelectAgent,
		client:   client,
		manager:  mgr,
		registry: reg,
	}
}

// Init starts the app by loading available agents and health monitoring.
func (m Model) Init() tea.Cmd {
	client := m.client
	loadAgents := func() tea.Msg {
		agents, err := client.ListAgents(context.Background())
		return AgentsLoadedMsg{Agents: agents, Err: err}
	}

	// Status bar heartbeat runs for the life of the app regardless of
	// whether a service manager is wired up. Using a slower interval so
	// the beat reads as a pulse rather than a spin.
	m.statusSpinner = atoms.Spinner{
		ID:       100,
		Style:    theme.Style{Status: theme.Success},
		Frames:   atoms.SpinnerHeartbeat,
		Interval: 120 * time.Millisecond,
	}

	cmds := []tea.Cmd{loadAgents, m.statusSpinner.Init()}
	if m.manager != nil {
		cmds = append(cmds, service.ServiceHealthTick(m.manager))
	}
	return tea.Batch(cmds...)
}

// Update handles all incoming messages.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.chat.SetSize(m.width, m.height-5)
		if m.gallery {
			pos := m.chat.SaveScrollPosition()
			firstLoad := pos == 0 && !m.galleryLoaded
			m.galleryLoaded = true
			m.chat.ClearMessages()
			for _, gm := range buildGalleryMessages(m.width) {
				m.chat.AppendMessage(gm)
			}
			if firstLoad {
				m.chat.GotoBottom()
			} else {
				m.chat.RestoreScrollPosition(pos)
			}
		}
		return m, nil

	case atoms.SpinnerTickMsg:
		// Route status-bar heartbeat ticks to our spinner. The chat model
		// handles its own spinner ticks separately.
		if msg.ID == m.statusSpinner.ID {
			var cmd tea.Cmd
			m.statusSpinner, cmd = m.statusSpinner.Update(msg)
			return m, cmd
		}
		// Forward other spinner ticks to the chat model.
		newChat, cmd := m.chat.Update(msg)
		m.chat = newChat
		return m, cmd

	case tea.KeyPressMsg:
		if msg.String() == "ctrl+c" {
			return m, tea.Quit
		}

	case AgentsLoadedMsg:
		if msg.Err != nil {
			m.loadErr = msg.Err
			return m, nil
		}
		m.agents = msg.Agents
		if m.demo {
			return m.handleDemoAgentsLoaded()
		}
		return m, nil

	case ConversationCreatedMsg:
		if msg.Err != nil {
			m.loadErr = msg.Err
			return m, nil
		}
		m.chat.SetConversationID(msg.ConversationID)
		m.phase = PhaseChat
		if m.demo {
			m.prefillNextInput()
		}
		return m, nil

	case chat.ResponseMsg:
		newChat, cmd := m.chat.Update(msg)
		m.chat = newChat
		// In demo mode, prefill next input after streaming completes
		if m.demo && msg.Chunk.Done {
			m.prefillNextInput()
		}
		return m, cmd

	case command.SwitchAgentMsg:
		m.phase = PhaseSelectAgent
		return m, nil

	case service.ServiceHealthMsg:
		m.healthStatuses = msg.Statuses
		if m.manager != nil {
			return m, service.ServiceHealthTick(m.manager)
		}
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
	keyMsg, ok := msg.(tea.KeyPressMsg)
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
			m.chat = chat.New(m.client, agent.Name, m.registry)
			m.chat.SetSize(m.width, m.height-5)

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
	if keyMsg, ok := msg.(tea.KeyPressMsg); ok {
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
func (m Model) View() tea.View {
	var body string
	if m.width < 30 {
		body = "resize terminal"
	} else {
		switch m.phase {
		case PhaseSelectAgent:
			body = m.viewAgentSelect()
		case PhaseChat:
			body = m.chat.RenderHeader() + "\n" + m.chat.View()
		}
		body += "\n" + m.renderLegend()
	}

	v := tea.NewView(body)
	v.AltScreen = true
	v.MouseMode = tea.MouseModeCellMotion
	return v
}

func (m Model) viewAgentSelect() string {
	ctx := atoms.DefaultContext(m.width)
	// Use a zero-width context for inline text rendering (no width padding)
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	var lines []string

	header := molecules.Header(ctx, molecules.HeaderData{
		Title: "STACK BENCH",
	})
	lines = append(lines, header)
	lines = append(lines, "")

	if m.loadErr != nil {
		errBlock := molecules.ErrorBlock(ctx, molecules.ErrorBlockData{
			Message:     fmt.Sprintf("%v", m.loadErr),
			Suggestions: []string{"Press q to quit."},
		})
		lines = append(lines, "  "+errBlock)
	} else if len(m.agents) == 0 {
		lines = append(lines, "  "+atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  "Loading agents...",
			Style: theme.Style{Hierarchy: theme.Tertiary},
		}))
	} else {
		lines = append(lines, "  "+atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text: "Select an agent to start a conversation:",
		}))
		lines = append(lines, "")

		for i, agent := range m.agents {
			cursor := "  "
			if i == m.agentCursor {
				cursor = atoms.Icon(inlineCtx, atoms.IconCursor, theme.Style{Category: theme.CatAgent}) + " "
			}

			name := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text: agent.Name,
			})
			if i == m.agentCursor {
				name = atoms.TextBlock(inlineCtx, atoms.TextBlockData{
					Text:  agent.Name,
					Style: theme.Style{Category: theme.CatAgent},
				})
			}

			role := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text:  agent.Role,
				Style: theme.Style{Hierarchy: theme.Tertiary},
			})
			lines = append(lines, fmt.Sprintf("  %s%s  %s", cursor, name, role))
		}
	}

	bodyH := m.height - 2
	for len(lines) < bodyH {
		lines = append(lines, "")
	}

	return lipgloss.NewStyle().Width(m.width).Height(bodyH).Render(
		strings.Join(lines, "\n"),
	)
}

func (m Model) renderLegend() string {
	ctx := atoms.DefaultContext(m.width)

	var hint string
	switch m.phase {
	case PhaseSelectAgent:
		hint = "j/k: navigate  enter: select  q: quit"
	case PhaseChat:
		hint = "enter: send  pgup/pgdn: scroll  esc: back  ctrl+c: quit"
	}

	// Map service health to molecule HealthState
	var health molecules.HealthState
	var serviceName string
	if m.manager != nil {
		serviceName = "backend"
		status, ok := m.healthStatuses["backend"]
		if !ok {
			status = service.StatusStarting
		}
		switch status {
		case service.StatusHealthy:
			health = molecules.HealthHealthy
		case service.StatusUnhealthy:
			health = molecules.HealthUnhealthy
		case service.StatusStarting:
			health = molecules.HealthStarting
		default:
			health = molecules.HealthUnknown
		}
	}

	return molecules.StatusBar(ctx, molecules.StatusBarData{
		Hints:       " " + hint,
		ServiceName: serviceName,
		Health:      health,
		Spinner:     &m.statusSpinner,
	})
}
