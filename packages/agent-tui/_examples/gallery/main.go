// Gallery example: scrollable showcase of all atoms and molecules.
//
// Usage: go run .
package main

import (
	"fmt"
	"os"

	tui "github.com/dugshub/agent-tui"
)

func main() {
	if err := tui.RunGallery(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
