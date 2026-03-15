package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/dugshub/stack-bench/cli/internal/api"
	"github.com/dugshub/stack-bench/cli/internal/app"
)

func main() {
	client := &api.StubClient{}
	model := app.New(client)

	p := tea.NewProgram(model, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
