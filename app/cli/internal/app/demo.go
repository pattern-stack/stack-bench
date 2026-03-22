package app

import (
	"context"
	"strings"
	"time"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/stack-bench/app/cli/internal/api"
	"github.com/dugshub/stack-bench/app/cli/internal/chat"
	"github.com/dugshub/stack-bench/app/cli/internal/command"
)

// DemoTickMsg signals that the next scripted user message should be injected.
type DemoTickMsg struct{}

// DemoRunner manages playback of a scripted demo conversation.
type DemoRunner struct {
	script       []api.DemoMessage
	userMessages []string
	cursor       int
}

// NewDemoRunner creates a runner that extracts user messages from the script.
func NewDemoRunner(script []api.DemoMessage) *DemoRunner {
	var userMsgs []string
	for _, m := range script {
		if m.Role == "user" {
			userMsgs = append(userMsgs, m.Content)
		}
	}
	return &DemoRunner{
		script:       script,
		userMessages: userMsgs,
	}
}

// NextUserMessage returns the next user message and whether one was available.
func (d *DemoRunner) NextUserMessage() (string, bool) {
	if d.cursor >= len(d.userMessages) {
		return "", false
	}
	msg := d.userMessages[d.cursor]
	d.cursor++
	return msg, true
}

// demoTickCmd returns a command that fires a DemoTickMsg after a delay.
func demoTickCmd(delay time.Duration) tea.Cmd {
	return func() tea.Msg {
		time.Sleep(delay)
		return DemoTickMsg{}
	}
}

// readingDelay calculates a pause proportional to content length.
// ~50ms per word, clamped to [1s, 4s].
func readingDelay(content string) time.Duration {
	words := len(strings.Fields(content))
	d := time.Duration(words) * 50 * time.Millisecond
	if d < 1*time.Second {
		d = 1 * time.Second
	}
	if d > 4*time.Second {
		d = 4 * time.Second
	}
	return d
}

// NewDemo creates a Model pre-configured for demo replay mode.
func NewDemo(script []api.DemoMessage) Model {
	client := api.NewDemoClient(script)
	reg := command.DefaultRegistry()
	return Model{
		width:      80,
		height:     24,
		phase:      PhaseSelectAgent,
		client:     client,
		registry:   reg,
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

// handleDemoTick injects the next user message and triggers a send.
func (m Model) handleDemoTick() (tea.Model, tea.Cmd) {
	text, ok := m.demoRunner.NextUserMessage()
	if !ok {
		return m, nil
	}

	// Append user message to chat
	m.chat.AppendMessage(chat.Message{Role: chat.RoleUser, Content: text})

	// Trigger the send via the client
	ch, err := m.client.SendMessage(context.Background(), m.chat.GetConversationID(), text)
	if err != nil {
		m.chat.AppendMessage(chat.Message{
			Role:    chat.RoleAssistant,
			Content: "Error: " + err.Error(),
		})
		return m, nil
	}
	m.chat.SetStreaming(true, ch)
	return m, readStreamCmd(ch)
}

// readStreamCmd reads the next chunk from a stream channel.
func readStreamCmd(ch <-chan api.StreamChunk) tea.Cmd {
	return func() tea.Msg {
		chunk, ok := <-ch
		if !ok {
			return chat.ResponseMsg{Chunk: api.StreamChunk{Done: true}}
		}
		return chat.ResponseMsg{Chunk: chunk}
	}
}
