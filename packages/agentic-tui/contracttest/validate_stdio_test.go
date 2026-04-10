package contracttest

import (
	"os/exec"
	"testing"
)

func TestValidateStdioBackend_Python(t *testing.T) {
	// Skip if python3 is not available
	if _, err := exec.LookPath("python3"); err != nil {
		t.Skip("python3 not available")
	}

	ValidateStdioBackend(t, "python3", "../_examples/stdio-python/agent.py")
}
