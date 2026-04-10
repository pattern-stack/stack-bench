// Example: use Claude CLI as the backend via JSON-RPC stdio bridge.
package main

import (
	"fmt"
	"os"

	tui "github.com/dugshub/agentic-tui"
)

func main() {
	app, err := tui.New(tui.Config{
		AppName:        "Claude",
		AssistantLabel: "claude:",
		BackendStdio: &tui.StdioConfig{
			Command: "python3",
			Args:    []string{"agent.py"},
			Dir:     ".",
		},
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
