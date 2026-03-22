package molecules

import (
	"strings"
	"testing"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

func TestToolCallBlock_ContainsToolName(t *testing.T) {
	out := ToolCallBlock(darkCtx(), ToolCallBlockData{
		ToolName: "read_file",
		State:    ToolCallPending,
	})
	if !strings.Contains(out, "read_file") {
		t.Error("expected tool call block to contain tool name")
	}
}

func TestToolCallBlock_PendingShowsCircle(t *testing.T) {
	out := ToolCallBlock(darkCtx(), ToolCallBlockData{
		ToolName: "write_file",
		State:    ToolCallPending,
	})
	if !strings.Contains(out, "○") {
		t.Error("expected pending state to show circle icon")
	}
}

func TestToolCallBlock_SuccessShowsCheck(t *testing.T) {
	out := ToolCallBlock(darkCtx(), ToolCallBlockData{
		ToolName: "read_file",
		State:    ToolCallSuccess,
	})
	if !strings.Contains(out, "✓") {
		t.Error("expected success state to show check icon")
	}
}

func TestToolCallBlock_ErrorShowsX(t *testing.T) {
	out := ToolCallBlock(darkCtx(), ToolCallBlockData{
		ToolName: "exec",
		State:    ToolCallError,
	})
	if !strings.Contains(out, "✗") {
		t.Error("expected error state to show X icon")
	}
}

func TestToolCallBlock_RunningShowsSpinner(t *testing.T) {
	s := atoms.NewSpinner(1, theme.Style{Status: theme.Running})
	out := ToolCallBlock(darkCtx(), ToolCallBlockData{
		ToolName: "search",
		State:    ToolCallRunning,
		Spinner:  s,
	})
	if !strings.Contains(out, atoms.SpinnerFrames[0]) {
		t.Error("expected running state to show spinner frame")
	}
}

func TestToolCallBlock_WithArgs(t *testing.T) {
	out := ToolCallBlock(darkCtx(), ToolCallBlockData{
		ToolName: "read_file",
		State:    ToolCallSuccess,
		Args:     "path=main.go",
	})
	if !strings.Contains(out, "path=main.go") {
		t.Error("expected tool call block to contain args")
	}
}

func TestToolCallBlock_WithResult(t *testing.T) {
	out := ToolCallBlock(darkCtx(), ToolCallBlockData{
		ToolName: "exec",
		State:    ToolCallSuccess,
		Result:   "exit code 0",
	})
	if !strings.Contains(out, "exit code 0") {
		t.Error("expected tool call block to contain result")
	}
}

func TestToolCallBlock_StatesRenderDifferently(t *testing.T) {
	s := atoms.NewSpinner(1, theme.Style{Status: theme.Running})
	states := []ToolCallState{ToolCallPending, ToolCallRunning, ToolCallSuccess, ToolCallError}
	outputs := make([]string, len(states))
	for i, state := range states {
		outputs[i] = ToolCallBlock(darkCtx(), ToolCallBlockData{
			ToolName: "test",
			State:    state,
			Spinner:  s,
		})
	}
	// At minimum success and error should differ
	if outputs[2] == outputs[3] {
		t.Error("expected success and error states to render differently")
	}
}

func TestToolCallBlock_LightTheme(t *testing.T) {
	out := ToolCallBlock(lightCtx(), ToolCallBlockData{
		ToolName: "grep",
		State:    ToolCallSuccess,
		Args:     "pattern=TODO",
	})
	if !strings.Contains(out, "grep") {
		t.Error("expected light theme tool call block to contain tool name")
	}
}
