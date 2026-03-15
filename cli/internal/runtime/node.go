package runtime

import "context"

// NodeStatus represents the health state of a managed node.
type NodeStatus int

const (
	StatusStopped NodeStatus = iota
	StatusStarting
	StatusHealthy
	StatusUnhealthy
)

func (s NodeStatus) String() string {
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

// AgentNode is a managed backend process that the CLI can start/stop.
type AgentNode interface {
	// Name returns a human-readable identifier for this node.
	Name() string

	// Start launches the node process and blocks until healthy or ctx is cancelled.
	Start(ctx context.Context) error

	// Stop gracefully shuts down the node process.
	Stop() error

	// Health returns the cached health status.
	Health() NodeStatus

	// CheckHealth performs an active health check and updates the cached status.
	CheckHealth() NodeStatus

	// BaseURL returns the HTTP base URL for this node's API.
	BaseURL() string
}
