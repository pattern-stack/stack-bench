package service

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"sync"
	"syscall"
	"time"
)

const (
	defaultHost        = "127.0.0.1"
	defaultPort        = 8000
	healthPollInterval = 200 * time.Millisecond
	healthTimeout      = 30 * time.Second
	stopGracePeriod    = 5 * time.Second
)

// ExecServiceConfig configures a process-based service node.
type ExecServiceConfig struct {
	Name       string
	Command    string
	Args       []string
	Dir        string
	Host       string
	Port       int
	HealthPath string
	Env        []string
}

// ExecService manages a backend process.
type ExecService struct {
	cfg ExecServiceConfig

	mu     sync.Mutex
	cmd    *exec.Cmd
	status ServiceStatus
	stderr bytes.Buffer
}

var _ ServiceNode = (*ExecService)(nil)

// NewExecService creates a node that spawns a process based on config.
func NewExecService(cfg ExecServiceConfig) *ExecService {
	if cfg.Host == "" {
		cfg.Host = defaultHost
	}
	if cfg.Port == 0 {
		cfg.Port = defaultPort
	}
	if cfg.HealthPath == "" {
		cfg.HealthPath = "/health"
	}
	if cfg.Name == "" {
		cfg.Name = "backend"
	}
	return &ExecService{
		cfg:    cfg,
		status: StatusStopped,
	}
}

func (n *ExecService) Name() string     { return n.cfg.Name }
func (n *ExecService) BaseURL() string   { return fmt.Sprintf("http://%s:%d", n.cfg.Host, n.cfg.Port) }

func (n *ExecService) Health() ServiceStatus {
	n.mu.Lock()
	defer n.mu.Unlock()
	return n.status
}

func (n *ExecService) setStatus(s ServiceStatus) {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.status = s
}

func (n *ExecService) Start(ctx context.Context) error {
	n.setStatus(StatusStarting)

	cmd := exec.CommandContext(ctx, n.cfg.Command, n.cfg.Args...)
	if n.cfg.Dir != "" {
		cmd.Dir = n.cfg.Dir
	}
	cmd.Stdout = io.Discard
	cmd.Stderr = &n.stderr
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	if len(n.cfg.Env) > 0 {
		cmd.Env = append(os.Environ(), n.cfg.Env...)
	}

	if err := cmd.Start(); err != nil {
		n.setStatus(StatusStopped)
		return fmt.Errorf("start %s: %w", n.cfg.Name, err)
	}

	n.mu.Lock()
	n.cmd = cmd
	n.mu.Unlock()

	exitedCh := make(chan struct{})
	go func() {
		cmd.Wait()
		close(exitedCh)
	}()

	healthURL := n.BaseURL() + n.cfg.HealthPath
	client := &http.Client{Timeout: 2 * time.Second}
	deadline := time.Now().Add(healthTimeout)

	for time.Now().Before(deadline) {
		select {
		case <-exitedCh:
			n.setStatus(StatusStopped)
			return fmt.Errorf("%s exited prematurely: %s", n.cfg.Name, strings.TrimSpace(n.stderr.String()))
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

	n.setStatus(StatusUnhealthy)
	return fmt.Errorf("%s did not become healthy within %s", n.cfg.Name, healthTimeout)
}

func (n *ExecService) Stop() error {
	n.mu.Lock()
	cmd := n.cmd
	n.mu.Unlock()

	if cmd == nil || cmd.Process == nil {
		n.setStatus(StatusStopped)
		return nil
	}

	pgid, err := syscall.Getpgid(cmd.Process.Pid)
	if err == nil {
		_ = syscall.Kill(-pgid, syscall.SIGTERM)
	} else {
		_ = cmd.Process.Signal(syscall.SIGTERM)
	}

	done := make(chan error, 1)
	go func() { done <- cmd.Wait() }()

	select {
	case <-done:
	case <-time.After(stopGracePeriod):
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

func (n *ExecService) CheckHealth() ServiceStatus {
	n.mu.Lock()
	if n.status == StatusStopped {
		n.mu.Unlock()
		return StatusStopped
	}
	n.mu.Unlock()

	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(n.BaseURL() + n.cfg.HealthPath)
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
