// Example: Gemini CLI as a backend via BackendCLI transport.
package main

import (
	"fmt"
	"os"

	tui "github.com/dugshub/agentic-tui"
)

func main() {
	app, err := tui.New(tui.Config{
		AppName:        "Gemini",
		AssistantLabel: "gemini:",
		BackendCLI: &tui.CLIAgentConfig{
			Command: "gemini",
			Args:    []string{"-p", "--output-format", "stream-json"},
			Format:  tui.FormatGemini,
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
