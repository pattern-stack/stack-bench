package tui

import (
	"github.com/dugshub/agentic-tui/internal/service"
)

// ServiceNode is a managed backend process.
type ServiceNode = service.ServiceNode

// ServiceStatus represents the health state of a managed service.
type ServiceStatus = service.ServiceStatus

// Re-export status constants.
const (
	StatusStopped   = service.StatusStopped
	StatusStarting  = service.StatusStarting
	StatusHealthy   = service.StatusHealthy
	StatusUnhealthy = service.StatusUnhealthy
)
