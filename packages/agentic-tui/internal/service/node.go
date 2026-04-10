package service

import "context"

// ServiceStatus represents the health state of a managed service.
type ServiceStatus int

const (
	StatusStopped ServiceStatus = iota
	StatusStarting
	StatusHealthy
	StatusUnhealthy
)

func (s ServiceStatus) String() string {
	switch s {
	case StatusStopped:
		return "stopped"
	case StatusStarting:
		return "starting"
	case StatusHealthy:
		return "healthy"
	case StatusUnhealthy:
		return "unhealthy"
	default:
		return "unknown"
	}
}

// ServiceNode is a managed backend process that the TUI can start/stop.
type ServiceNode interface {
	Name() string
	Start(ctx context.Context) error
	Stop() error
	Health() ServiceStatus
	CheckHealth() ServiceStatus
	BaseURL() string
}
