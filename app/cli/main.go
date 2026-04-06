package main

import (
	"fmt"
	"os"
	"path/filepath"

	tui "github.com/dugshub/agent-tui"
)

func main() {
	app, err := tui.New(tui.Config{
		AppName:        "Stack Bench",
		AssistantLabel: "sb:",
		EnvOverride:    "SB_BACKEND_URL",
		BackendService: tui.NewExecService(tui.ExecServiceConfig{
			Name:    "backend",
			Command: "uv",
			Args:    []string{"run", "uvicorn", "organisms.api.app:app", "--host", "127.0.0.1", "--port", "8000"},
			Dir:     findBackendDir(),
			Port:    8000,
		}),
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	if err := app.Run(); err != nil {
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
