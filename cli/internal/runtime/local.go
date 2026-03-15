package runtime

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"sync"
	"syscall"
	"time"
)

const (
	defaultHost       = "127.0.0.1"
	defaultPort       = 8000
	healthPollInterval = 200 * time.Millisecond
	healthTimeout      = 30 * time.Second
	stopGracePeriod    = 5 * time.Second
)

// LocalNode manages a local backend process via uvicorn.
type LocalNode struct {
	host       string
	port       int
	backendDir string

	mu     sync.Mutex
	cmd    *exec.Cmd
	status NodeStatus
	stderr bytes.Buffer
}

var _ AgentNode = (*LocalNode)(nil)

// NewLocalNode creates a node that spawns the backend from the given directory.
func NewLocalNode(backendDir string) *LocalNode {
	return &LocalNode{
		host:       defaultHost,
		port:       defaultPort,
		backendDir: backendDir,
		status:     StatusStopped,
	}
}

func (n *LocalNode) Name() string {
	return "backend"
}

func (n *LocalNode) BaseURL() string {
	return fmt.Sprintf("http://%s:%d", n.host, n.port)
}

func (n *LocalNode) Health() NodeStatus {
	n.mu.Lock()
	defer n.mu.Unlock()
	return n.status
}

func (n *LocalNode) setStatus(s NodeStatus) {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.status = s
}

func (n *LocalNode) Start(ctx context.Context) error {
	n.setStatus(StatusStarting)

	cmd := exec.CommandContext(ctx, "uv", "run", "uvicorn",
		"organisms.api.app:app",
		"--host", n.host,
		"--port", fmt.Sprintf("%d", n.port),
	)
	cmd.Dir = n.backendDir
	cmd.Stdout = io.Discard
	// stderr is captured for startup failure diagnostics only
	cmd.Stderr = &n.stderr
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	if err := cmd.Start(); err != nil {
		n.setStatus(StatusStopped)
		return fmt.Errorf("start backend: %w", err)
	}

	n.mu.Lock()
	n.cmd = cmd
	n.mu.Unlock()

	// Detect early process exit
	exitedCh := make(chan struct{})
	go func() {
		n.cmd.Wait()
		close(exitedCh)
	}()

	// Poll health endpoint until ready
	healthURL := n.BaseURL() + "/health"
	client := &http.Client{Timeout: 2 * time.Second}
	deadline := time.Now().Add(healthTimeout)

	for time.Now().Before(deadline) {
		select {
		case <-exitedCh:
			n.setStatus(StatusStopped)
			return fmt.Errorf("backend process exited prematurely: %s", n.stderr.String())
		case <-ctx.Done():
			_ = n.Stop()
			return ctx.Err()
		default:
		}

		resp, err := client.Get(healthURL)
		if err == nil {
			resp.Body.Close()
			if resp.StatusCode == http.StatusOK {
				n.setStatus(StatusHealthy)
				n.stderr.Reset()
				return nil
			}
		}

		time.Sleep(healthPollInterval)
	}

	// Timed out waiting for health
	n.setStatus(StatusUnhealthy)
	return fmt.Errorf("backend did not become healthy within %s", healthTimeout)
}

func (n *LocalNode) Stop() error {
	n.mu.Lock()
	cmd := n.cmd
	n.mu.Unlock()

	if cmd == nil || cmd.Process == nil {
		n.setStatus(StatusStopped)
		return nil
	}

	// Send SIGTERM to the process group
	pgid, err := syscall.Getpgid(cmd.Process.Pid)
	if err == nil {
		_ = syscall.Kill(-pgid, syscall.SIGTERM)
	} else {
		_ = cmd.Process.Signal(syscall.SIGTERM)
	}

	// Wait for graceful shutdown
	done := make(chan error, 1)
	go func() {
		done <- cmd.Wait()
	}()

	select {
	case <-done:
		// Exited gracefully
	case <-time.After(stopGracePeriod):
		// Force kill the process group
		if pgid, err := syscall.Getpgid(cmd.Process.Pid); err == nil {
			_ = syscall.Kill(-pgid, syscall.SIGKILL)
		} else {
			_ = cmd.Process.Kill()
		}
		<-done
	}

	n.mu.Lock()
	n.cmd = nil
	n.status = StatusStopped
	n.mu.Unlock()

	return nil
}

// CheckHealth performs an active health check and updates the cached status.
func (n *LocalNode) CheckHealth() NodeStatus {
	n.mu.Lock()
	if n.status == StatusStopped {
		n.mu.Unlock()
		return StatusStopped
	}
	n.mu.Unlock()

	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(n.BaseURL() + "/health")
	if err != nil {
		n.setStatus(StatusUnhealthy)
		return StatusUnhealthy
	}
	resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		n.setStatus(StatusHealthy)
		return StatusHealthy
	}

	n.setStatus(StatusUnhealthy)
	return StatusUnhealthy
}
