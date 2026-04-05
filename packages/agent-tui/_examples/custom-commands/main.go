// Example: custom slash commands.
package main

import (
	"fmt"
	"os"

	tea "charm.land/bubbletea/v2"
	tui "github.com/dugshub/agent-tui"
)

func main() {
	app, err := tui.New(tui.Config{
		AppName:    "My Agent",
		BackendURL: "http://localhost:8000",
		Commands: []tui.CommandDef{
			{
				Name:        "deploy",
				Aliases:     []string{"d"},
				Description: "Deploy the current project",
				Category:    "operations",
				Handler: func(_ tui.CommandParseResult) tea.Cmd {
					return nil
				},
			},
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
