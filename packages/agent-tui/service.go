package tui

import (
	"github.com/dugshub/agent-tui/internal/service"
)

// ServiceNode is a managed backend process.
// This is a type alias for the internal service.ServiceNode interface.
type ServiceNode = service.ServiceNode

// ServiceStatus represents the health state of a managed service.
type ServiceStatus = service.ServiceStatus

// Re-export status constants.
const (
	StatusStopped    = service.StatusStopped
	StatusStarting   = service.StatusStarting
	StatusHealthy    = service.StatusHealthy
	StatusUnhealthy  = service.StatusUnhealthy
)

// ExecServiceConfig configures the built-in exec-based service node.
type ExecServiceConfig = service.ExecServiceConfig

// NewExecService creates a ServiceNode that starts a process via exec.
func NewExecService(cfg ExecServiceConfig) ServiceNode {
	return service.NewExecService(cfg)
}
