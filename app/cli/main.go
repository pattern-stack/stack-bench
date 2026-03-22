package main

import (
	"context"
	_ "embed"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/stack-bench/app/cli/internal/api"
	"github.com/dugshub/stack-bench/app/cli/internal/app"
	"github.com/dugshub/stack-bench/app/cli/internal/service"
)

//go:embed fixtures/demo.json
var embeddedDemoScript []byte

func main() {
	noBackend := flag.Bool("no-backend", false, "skip auto-starting the backend server")
	demoMode := flag.Bool("demo", false, "run in demo mode with scripted conversation replay")
	demoScript := flag.String("demo-script", "", "path to demo script JSON (default: built-in fixture)")
	galleryMode := flag.Bool("demo-gallery", false, "show component gallery with all atoms and molecules")
	flag.Parse()

	if *galleryMode {
		runGallery()
		return
	}

	if *demoMode {
		runDemo(*demoScript)
		return
	}

	var client api.Client
	var mgr *service.ServiceManager

	if baseURL := os.Getenv("SB_BACKEND_URL"); baseURL != "" {
		// Explicit URL: use it directly, no managed backend
		client = api.NewHTTPClient(baseURL)
	} else if *noBackend {
		// No backend requested: use stub
		client = &api.StubClient{}
	} else {
		// Auto-start backend
		backendDir := findBackendDir()
		node := service.NewLocalService(backendDir)
		mgr = service.NewServiceManager(node)

		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()

		fmt.Fprintf(os.Stderr, "Starting backend...\n")
		if err := mgr.StartAll(ctx); err != nil {
			fmt.Fprintf(os.Stderr, "Error starting backend: %v\n", err)
			os.Exit(1)
		}
		defer mgr.StopAll()

		client = api.NewHTTPClient(node.BaseURL())
	}

	// Handle signals for clean shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigCh
		if mgr != nil {
			mgr.StopAll()
		}
		os.Exit(0)
	}()

	model := app.New(client, mgr)

	p := tea.NewProgram(model)
	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		if mgr != nil {
			mgr.StopAll()
		}
		os.Exit(1)
	}
}

func runDemo(scriptPath string) {
	var data []byte
	if scriptPath != "" {
		var err error
		data, err = os.ReadFile(scriptPath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error reading demo script: %v\n", err)
			os.Exit(1)
		}
	} else {
		data = embeddedDemoScript
	}

	var script []api.DemoMessage
	if err := json.Unmarshal(data, &script); err != nil {
		fmt.Fprintf(os.Stderr, "Error parsing demo script: %v\n", err)
		os.Exit(1)
	}

	model := app.NewDemo(script)
	p := tea.NewProgram(model)
	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runGallery() {
	model := app.NewGallery()
	p := tea.NewProgram(model)
	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

// findBackendDir locates the backend/ directory relative to the executable or cwd.
func findBackendDir() string {
	// Try relative to cwd first (common during development)
	candidates := []string{
		"backend",
		"../backend",
	}

	// Also try relative to the executable
	if exe, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exe)
		candidates = append(candidates,
			filepath.Join(exeDir, "backend"),
			filepath.Join(exeDir, "..", "backend"),
		)
	}

	for _, dir := range candidates {
		abs, err := filepath.Abs(dir)
		if err != nil {
			continue
		}
		if info, err := os.Stat(abs); err == nil && info.IsDir() {
			return abs
		}
	}

	// Fallback: assume backend/ exists in cwd
	return "backend"
}
