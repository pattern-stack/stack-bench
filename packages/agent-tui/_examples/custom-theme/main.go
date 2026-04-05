// Example: custom Nord-inspired theme.
package main

import (
	"fmt"
	"os"

	"charm.land/lipgloss/v2"
	tui "github.com/dugshub/agent-tui"
)

func main() {
	nord := tui.DarkTheme()
	nord.Name = "nord"
	nord.Categories[tui.CatAgent] = lipgloss.Color("#88C0D0")
	nord.Categories[tui.CatTool] = lipgloss.Color("#EBCB8B")

	app, err := tui.New(tui.Config{
		AppName:    "Nord Agent",
		BackendURL: "http://localhost:8000",
		Theme:      nord,
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
