// Example: Claude Code CLI as a backend via BackendCLI transport.
// No bridge script needed — agentic-tui parses Claude's stream-json directly.
package main

import (
	"fmt"
	"os"

	tui "github.com/dugshub/agentic-tui"
)

func main() {
	app, err := tui.New(tui.Config{
		AppName:        "Claude Code",
		AssistantLabel: "claude:",
		BackendCLI: &tui.CLIAgentConfig{
			Command: "claude",
			Args:    []string{"-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages", "--bare", "--model", "sonnet"},
			Format:  tui.FormatClaude,
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
