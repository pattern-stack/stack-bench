package app

import (
	"context"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/agentic-tui/internal/demo"
	"github.com/dugshub/agentic-tui/internal/chat"
	"github.com/dugshub/agentic-tui/internal/command"
)

// DemoRunner tracks position through a scripted conversation's user messages.
type DemoRunner struct {
	userMessages []string
	cursor       int
}

// NewDemoRunner extracts user messages from a script for sequential replay.
func NewDemoRunner(script []demo.DemoMessage) *DemoRunner {
	var msgs []string
	for _, m := range script {
		if m.Role == "user" {
			msgs = append(msgs, m.Content)
		}
	}
	return &DemoRunner{userMessages: msgs}
}

// NextUserMessage returns the next user message, advancing the cursor.
func (d *DemoRunner) NextUserMessage() (string, bool) {
	if d.cursor >= len(d.userMessages) {
		return "", false
	}
	msg := d.userMessages[d.cursor]
	d.cursor++
	return msg, true
}

// NewDemo creates a Model pre-configured for demo mode.
// Auto-selects the demo agent and prefills chat input from the script.
func NewDemo(script []demo.DemoMessage) Model {
	client := demo.NewDemoClient(script)
	return Model{
		width:      80,
		height:     24,
		phase:      PhaseSelectAgent,
		client:     client,
		registry:   command.DefaultRegistry(),
		demo:       true,
		demoRunner: NewDemoRunner(script),
	}
}

// handleDemoAgentsLoaded auto-selects the first agent and creates a conversation.
func (m Model) handleDemoAgentsLoaded() (tea.Model, tea.Cmd) {
	if len(m.agents) == 0 {
		return m, nil
	}
	agent := m.agents[0]
	m.chat = chat.New(m.client, agent.Name, m.registry)
	m.chat.SetSize(m.width, m.height-2)

	client := m.client
	agentID := agent.ID
	return m, func() tea.Msg {
		id, err := client.CreateConversation(context.Background(), agentID)
		return ConversationCreatedMsg{ConversationID: id, Err: err}
	}
}

// prefillNextInput sets the chat input to the next scripted user message.
func (m *Model) prefillNextInput() {
	if m.demoRunner == nil {
		return
	}
	if text, ok := m.demoRunner.NextUserMessage(); ok {
		m.chat.SetInput(text)
	}
}
