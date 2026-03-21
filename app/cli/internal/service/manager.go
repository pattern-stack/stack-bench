package service

import (
	"context"
	"time"

	tea "charm.land/bubbletea/v2"
)

const healthTickInterval = 3 * time.Second

// ServiceHealthMsg is sent periodically with updated node health statuses.
type ServiceHealthMsg struct {
	Statuses map[string]ServiceStatus
}

// ServiceManager coordinates the lifecycle of all managed nodes.
type ServiceManager struct {
	nodes []ServiceNode
}

// NewServiceManager creates a manager for the given nodes.
func NewServiceManager(nodes ...ServiceNode) *ServiceManager {
	return &ServiceManager{nodes: nodes}
}

// StartAll starts all nodes in order. Returns on first error.
func (m *ServiceManager) StartAll(ctx context.Context) error {
	for _, node := range m.nodes {
		if err := node.Start(ctx); err != nil {
			return err
		}
	}
	return nil
}

// StopAll stops all nodes in reverse order.
func (m *ServiceManager) StopAll() {
	for i := len(m.nodes) - 1; i >= 0; i-- {
		_ = m.nodes[i].Stop()
	}
}

// HealthSummary returns the current status of all nodes.
func (m *ServiceManager) HealthSummary() map[string]ServiceStatus {
	result := make(map[string]ServiceStatus, len(m.nodes))
	for _, node := range m.nodes {
		result[node.Name()] = node.Health()
	}
	return result
}

// Nodes returns the managed nodes.
func (m *ServiceManager) Nodes() []ServiceNode {
	return m.nodes
}

// ServiceHealthTick returns a tea.Cmd that performs health checks and sends a ServiceHealthMsg.
// Chain it to repeat: return the cmd again from Update when you receive ServiceHealthMsg.
func ServiceHealthTick(mgr *ServiceManager) tea.Cmd {
	return tea.Tick(healthTickInterval, func(_ time.Time) tea.Msg {
		// Perform active health checks on all nodes
		for _, node := range mgr.Nodes() {
			node.CheckHealth()
		}
		return ServiceHealthMsg{Statuses: mgr.HealthSummary()}
	})
}
