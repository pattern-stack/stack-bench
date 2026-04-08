// Demo example: exercises every rendering path in agent-tui.
//
// Usage: go run .
// Usage: go run . --script path/to/custom.json
package main

import (
	_ "embed"
	"encoding/json"
	"flag"
	"fmt"
	"os"

	tui "github.com/dugshub/agent-tui"
)

//go:embed fixture.json
var embeddedFixture []byte

func main() {
	scriptPath := flag.String("script", "", "path to demo script JSON (default: built-in fixture)")
	flag.Parse()

	var data []byte
	if *scriptPath != "" {
		var err error
		data, err = os.ReadFile(*scriptPath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error reading script: %v\n", err)
			os.Exit(1)
		}
	} else {
		data = embeddedFixture
	}

	var script []tui.DemoStep
	if err := json.Unmarshal(data, &script); err != nil {
		fmt.Fprintf(os.Stderr, "Error parsing script: %v\n", err)
		os.Exit(1)
	}

	app, err := tui.NewDemoApp(script, tui.Config{
		AppName:        "Demo",
		AssistantLabel: "agent:",
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
