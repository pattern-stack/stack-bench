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

// ServiceNode is a managed backend process that the CLI can start/stop.
type ServiceNode interface {
	// Name returns a human-readable identifier for this node.
	Name() string

	// Start launches the node process and blocks until healthy or ctx is cancelled.
	Start(ctx context.Context) error

	// Stop gracefully shuts down the node process.
	Stop() error

	// Health returns the cached health status.
	Health() ServiceStatus

	// CheckHealth performs an active health check and updates the cached status.
	CheckHealth() ServiceStatus

	// BaseURL returns the HTTP base URL for this node's API.
	BaseURL() string
}
