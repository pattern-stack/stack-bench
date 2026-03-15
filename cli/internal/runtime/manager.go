package runtime

import (
	"context"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

const healthTickInterval = 3 * time.Second

// HealthTickMsg is sent periodically with updated node health statuses.
type HealthTickMsg struct {
	Statuses map[string]NodeStatus
}

// Manager coordinates the lifecycle of all managed nodes.
type Manager struct {
	nodes []AgentNode
}

// NewManager creates a manager for the given nodes.
func NewManager(nodes ...AgentNode) *Manager {
	return &Manager{nodes: nodes}
}

// StartAll starts all nodes in order. Returns on first error.
func (m *Manager) StartAll(ctx context.Context) error {
	for _, node := range m.nodes {
		if err := node.Start(ctx); err != nil {
			return err
		}
	}
	return nil
}

// StopAll stops all nodes in reverse order.
func (m *Manager) StopAll() {
	for i := len(m.nodes) - 1; i >= 0; i-- {
		_ = m.nodes[i].Stop()
	}
}

// HealthSummary returns the current status of all nodes.
func (m *Manager) HealthSummary() map[string]NodeStatus {
	result := make(map[string]NodeStatus, len(m.nodes))
	for _, node := range m.nodes {
		result[node.Name()] = node.Health()
	}
	return result
}

// Nodes returns the managed nodes.
func (m *Manager) Nodes() []AgentNode {
	return m.nodes
}

// HealthTick returns a tea.Cmd that performs health checks and sends a HealthTickMsg.
// Chain it to repeat: return the cmd again from Update when you receive HealthTickMsg.
func HealthTick(mgr *Manager) tea.Cmd {
	return tea.Tick(healthTickInterval, func(_ time.Time) tea.Msg {
		// Perform active health checks on all nodes
		for _, node := range mgr.Nodes() {
			node.CheckHealth()
		}
		return HealthTickMsg{Statuses: mgr.HealthSummary()}
	})
}
