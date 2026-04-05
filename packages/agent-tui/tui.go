package tui

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/agent-tui/internal/app"
	"github.com/dugshub/agent-tui/internal/command"
	"github.com/dugshub/agent-tui/internal/service"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// App is a configured TUI application.
type App struct {
	cfg    Config
	client Client
	mgr    *service.ServiceManager
}

// New creates a configured TUI application.
func New(cfg Config) (*App, error) {
	if cfg.AppName == "" {
		return nil, fmt.Errorf("agent-tui: Config.AppName is required")
	}

	if cfg.AssistantLabel == "" {
		cfg.AssistantLabel = strings.ToLower(cfg.AppName) + ":"
	}

	// Set theme
	// TODO(v0.2): theme.SetActive mutates a package-level global, so two App
	// instances with different themes in the same process would conflict.
	// Acceptable for v0.1 since a single TUI per process is the expected use.
	if cfg.Theme != nil {
		theme.SetActive(cfg.Theme)
	}

	a := &App{cfg: cfg}

	// Resolve backend
	if err := a.resolveBackend(); err != nil {
		return nil, err
	}

	return a, nil
}

func (a *App) resolveBackend() error {
	cfg := a.cfg

	// Check env override first
	if cfg.EnvOverride != "" {
		if url := os.Getenv(cfg.EnvOverride); url != "" {
			a.client = newHTTPClient(url, cfg.Endpoints)
			return nil
		}
	}

	backends := 0
	if cfg.BackendURL != "" {
		backends++
	}
	if cfg.BackendService != nil {
		backends++
	}
	if cfg.BackendStdio != nil {
		backends++
	}

	if backends == 0 && cfg.EnvOverride == "" {
		return fmt.Errorf("agent-tui: one of BackendURL, BackendService, or BackendStdio must be set")
	}
	if backends > 1 {
		return fmt.Errorf("agent-tui: only one of BackendURL, BackendService, or BackendStdio may be set")
	}

	switch {
	case cfg.BackendURL != "":
		a.client = newHTTPClient(cfg.BackendURL, cfg.Endpoints)
	case cfg.BackendService != nil:
		a.mgr = service.NewServiceManager(cfg.BackendService)
		a.client = newHTTPClient(cfg.BackendService.BaseURL(), cfg.Endpoints)
	case cfg.BackendStdio != nil:
		client, err := newStdioClient(*cfg.BackendStdio)
		if err != nil {
			return fmt.Errorf("agent-tui: stdio client: %w", err)
		}
		a.client = client
	case cfg.EnvOverride != "":
		// Env var was set but empty — use stub
		a.client = newStubClient()
	}

	return nil
}

// Run starts the TUI. Blocks until the user quits.
func (a *App) Run() error {
	// Start managed service if needed
	if a.mgr != nil {
		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()

		fmt.Fprintf(os.Stderr, "Starting %s...\n", a.cfg.AppName)
		if err := a.mgr.StartAll(ctx); err != nil {
			return fmt.Errorf("start backend: %w", err)
		}
		defer a.mgr.StopAll()
	}

	// Handle signals
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigCh
		if a.mgr != nil {
			a.mgr.StopAll()
		}
		os.Exit(0)
	}()

	// Build command registry
	reg := a.buildRegistry()

	// Create app model
	appCfg := app.Config{
		AppName:        a.cfg.AppName,
		AssistantLabel: a.cfg.AssistantLabel,
	}
	internalClient := &internalClientAdapter{client: a.client}
	model := app.New(internalClient, a.mgr, reg, appCfg)

	p := tea.NewProgram(model)
	if _, err := p.Run(); err != nil {
		if a.mgr != nil {
			a.mgr.StopAll()
		}
		return err
	}

	return nil
}

func (a *App) buildRegistry() *command.Registry {
	reg := command.DefaultRegistry()

	for _, def := range a.cfg.Commands {
		reg.Register(command.Def{
			Name:        def.Name,
			Aliases:     def.Aliases,
			Description: def.Description,
			Category:    def.Category,
			Hidden:      def.Hidden,
			Handler: func(result command.ParseResult) tea.Cmd {
				if def.Handler != nil {
					return def.Handler(CommandParseResult{
						Command: result.Command,
						Args:    result.Args,
						Flags:   result.Flags,
						Options: result.Options,
						Raw:     result.Raw,
					})
				}
				return nil
			},
		})
	}

	return reg
}
