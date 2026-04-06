// Minimal agent-tui example: connect to a remote backend.
package main

import (
	"fmt"
	"os"

	tui "github.com/dugshub/agent-tui"
)

func main() {
	app, err := tui.New(tui.Config{
		AppName:    "My Agent",
		BackendURL: "http://localhost:8000",
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
