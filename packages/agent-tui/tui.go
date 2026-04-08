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
	"github.com/dugshub/agent-tui/internal/httpclient"
	"github.com/dugshub/agent-tui/internal/service"
	"github.com/dugshub/agent-tui/internal/sse"
	"github.com/dugshub/agent-tui/internal/stdioclient"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// App is a configured TUI application.
type App struct {
	cfg            Config
	internalClient sse.Client         // used for built-in backends (no conversion)
	customClient   Client             // non-nil only when consumer provides a custom Client
	mgr            *service.ServiceManager
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
			a.internalClient = newInternalHTTPClient(url, cfg.Endpoints)
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
		a.internalClient = newInternalHTTPClient(cfg.BackendURL, cfg.Endpoints)
	case cfg.BackendService != nil:
		a.mgr = service.NewServiceManager(cfg.BackendService)
		a.internalClient = newInternalHTTPClient(cfg.BackendService.BaseURL(), cfg.Endpoints)
	case cfg.BackendStdio != nil:
		c, err := stdioclient.New(stdioclient.Config{
			Command: cfg.BackendStdio.Command,
			Args:    cfg.BackendStdio.Args,
			Dir:     cfg.BackendStdio.Dir,
			Env:     cfg.BackendStdio.Env,
		})
		if err != nil {
			return fmt.Errorf("agent-tui: stdio client: %w", err)
		}
		a.internalClient = c
	case cfg.EnvOverride != "":
		// Env var was set but empty — use stub
		a.internalClient = &httpclient.StubClient{}
	}

	return nil
}

// sseClient returns the sse.Client to pass to the app model.
// For built-in backends, this is the internal client directly (no conversion).
// For custom Client implementations, it wraps via internalClientAdapter.
func (a *App) sseClient() sse.Client {
	if a.internalClient != nil {
		return a.internalClient
	}
	return &internalClientAdapter{client: a.customClient}
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

	// Create app model — pass sse.Client directly, no double conversion
	appCfg := app.Config{
		AppName:        a.cfg.AppName,
		AssistantLabel: a.cfg.AssistantLabel,
	}
	model := app.New(a.sseClient(), a.mgr, reg, appCfg)

	p := tea.NewProgram(model)
	if _, err := p.Run(); err != nil {
		if a.mgr != nil {
			a.mgr.StopAll()
		}
		return err
	}

	return nil
}

// RunGallery launches the component gallery — a scrollable showcase of all
// atoms and molecules pre-rendered. No backend required.
func RunGallery() error {
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

// newInternalHTTPClient creates an sse.Client backed by HTTP.
func newInternalHTTPClient(baseURL string, endpoints *EndpointConfig) sse.Client {
	var epCfg *httpclient.EndpointConfig
	if endpoints != nil {
		epCfg = &httpclient.EndpointConfig{
			ListAgents:         endpoints.ListAgents,
			CreateConversation: endpoints.CreateConversation,
			SendMessage:        endpoints.SendMessage,
			ListConversations:  endpoints.ListConversations,
			GetConversation:    endpoints.GetConversation,
			Health:             endpoints.Health,
		}
	}
	return httpclient.New(baseURL, epCfg)
}
