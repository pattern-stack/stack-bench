package tui

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/agentic-tui/internal/app"
	"github.com/dugshub/agentic-tui/internal/command"
	"github.com/dugshub/agentic-tui/internal/httpclient"
	"github.com/dugshub/agentic-tui/internal/service"
	"github.com/dugshub/agentic-tui/internal/types"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

// App is a configured TUI application.
type App struct {
	cfg    Config
	client types.Client
	mgr    *service.ServiceManager
}

// New creates a configured TUI application.
func New(cfg Config) (*App, error) {
	if cfg.AppName == "" {
		return nil, fmt.Errorf("agentic-tui: Config.AppName is required")
	}

	if cfg.AssistantLabel == "" {
		cfg.AssistantLabel = strings.ToLower(cfg.AppName) + ":"
	}

	// Set theme — register custom theme then activate by name
	if cfg.Theme != nil {
		theme.Register(cfg.Theme)
		theme.SetActive(cfg.Theme.Name)
	}

	a := &App{cfg: cfg}

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
			a.client = httpclient.NewHTTPClient(url)
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
		return fmt.Errorf("agentic-tui: one of BackendURL, BackendService, or BackendStdio must be set")
	}
	if backends > 1 {
		return fmt.Errorf("agentic-tui: only one of BackendURL, BackendService, or BackendStdio may be set")
	}

	switch {
	case cfg.BackendURL != "":
		a.client = httpclient.NewHTTPClient(cfg.BackendURL)
	case cfg.BackendService != nil:
		a.mgr = service.NewServiceManager(cfg.BackendService)
		a.client = httpclient.NewHTTPClient(cfg.BackendService.BaseURL())
	case cfg.BackendStdio != nil:
		c, err := NewStdioClient(*cfg.BackendStdio)
		if err != nil {
			return fmt.Errorf("agentic-tui: stdio client: %w", err)
		}
		a.client = c
	case cfg.EnvOverride != "":
		// Env var was set but empty — use stub
		a.client = &httpclient.StubClient{}
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
	model := app.New(a.client, a.mgr, reg, appCfg)

	p := tea.NewProgram(model)
	if _, err := p.Run(); err != nil {
		if a.mgr != nil {
			a.mgr.StopAll()
		}
		return err
	}

	return nil
}

// RunGallery starts the TUI in component gallery mode.
func (a *App) RunGallery() error {
	model := app.NewGallery()

	p := tea.NewProgram(model)
	if _, err := p.Run(); err != nil {
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
