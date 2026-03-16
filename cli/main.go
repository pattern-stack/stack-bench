package main

import (
	"fmt"
	"os"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/stack-bench/cli/internal/api"
	"github.com/dugshub/stack-bench/cli/internal/app"
)

func main() {
	client := &api.StubClient{}
	model := app.New(client)

	p := tea.NewProgram(model)
	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
