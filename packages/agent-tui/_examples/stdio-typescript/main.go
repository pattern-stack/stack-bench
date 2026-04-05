// Example: spawn a TypeScript backend via JSON-RPC over stdin/stdout.
package main

import (
	"fmt"
	"os"

	tui "github.com/dugshub/agent-tui"
)

func main() {
	app, err := tui.New(tui.Config{
		AppName: "TypeScript Agent",
		BackendStdio: &tui.StdioConfig{
			Command: "npx",
			Args:    []string{"tsx", "agent.ts"},
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
