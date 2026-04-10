// Standalone demo modes — no backend needed.
//
//	go run . --demo           Scripted conversation replay
//	go run . --gallery        Component showcase
//	go run . --spinners       All spinner presets
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"

	"github.com/dugshub/agentic-tui/internal/app"
	"github.com/dugshub/agentic-tui/internal/demo"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

func main() {
	demoMode := flag.Bool("demo", false, "scripted conversation replay")
	galleryMode := flag.Bool("gallery", false, "component showcase")
	spinnersMode := flag.Bool("spinners", false, "all spinner presets")
	flag.Parse()

	// Auto-detect theme
	if !lipgloss.HasDarkBackground(os.Stdin, os.Stdout) {
		theme.SetActive("light")
	}

	switch {
	case *galleryMode:
		run(app.NewGallery())
	case *spinnersMode:
		run(app.NewSpinnerGallery())
	case *demoMode:
		script := loadScript()
		run(app.NewDemo(script))
	default:
		fmt.Fprintln(os.Stderr, "Usage: go run . --demo | --gallery | --spinners")
		os.Exit(1)
	}
}

func run(model tea.Model) {
	p := tea.NewProgram(model)
	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func loadScript() []demo.DemoMessage {
	data, err := os.ReadFile("../../demo/fixtures/demo-parts.json")
	if err != nil {
		data, err = os.ReadFile("demo/fixtures/demo-parts.json")
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error reading demo script: %v\n", err)
			os.Exit(1)
		}
	}
	var script []demo.DemoMessage
	if err := json.Unmarshal(data, &script); err != nil {
		fmt.Fprintf(os.Stderr, "Error parsing demo script: %v\n", err)
		os.Exit(1)
	}
	return script
}
