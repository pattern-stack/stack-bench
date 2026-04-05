package molecules

import (
	"strings"
	"testing"

	"github.com/dugshub/agent-tui/internal/ui/theme"
)

func TestToolCallBlockRunning(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := ToolCallBlock(ctx, ToolCallData{
		Name:   "edit_file",
		Status: ToolRunning,
	})
	if !strings.Contains(result, "edit_file") {
		t.Error("should contain tool name")
	}
	if !strings.Contains(result, "running") {
		t.Error("should contain 'running' status label")
	}
}

func TestToolCallBlockSuccess(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := ToolCallBlock(ctx, ToolCallData{
		Name:   "read_file",
		Status: ToolSuccess,
	})
	if !strings.Contains(result, "read_file") {
		t.Error("should contain tool name")
	}
	if !strings.Contains(result, "done") {
		t.Error("should contain 'done' status label")
	}
}

func TestToolCallBlockError(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := ToolCallBlock(ctx, ToolCallData{
		Name:      "write_file",
		Status:    ToolError,
		Error:     "permission denied",
		Collapsed: false,
	})
	if !strings.Contains(result, "write_file") {
		t.Error("should contain tool name")
	}
	if !strings.Contains(result, "failed") {
		t.Error("should contain 'failed' status label")
	}
	if !strings.Contains(result, "permission denied") {
		t.Error("should contain error text")
	}
}

func TestToolCallBlockCollapsed(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := ToolCallBlock(ctx, ToolCallData{
		Name:      "edit_file",
		Status:    ToolSuccess,
		Input:     "some input data",
		Output:    "some output data",
		Collapsed: true,
	})
	if strings.Contains(result, "some input data") {
		t.Error("collapsed block should hide input")
	}
	if strings.Contains(result, "some output data") {
		t.Error("collapsed block should hide output")
	}
}

func TestToolCallBlockExpanded(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := ToolCallBlock(ctx, ToolCallData{
		Name:      "edit_file",
		Status:    ToolSuccess,
		Input:     "file: main.go",
		Output:    "ok",
		Collapsed: false,
	})
	if !strings.Contains(result, "file: main.go") {
		t.Error("expanded block should show input")
	}
	if !strings.Contains(result, "ok") {
		t.Error("expanded block should show output")
	}
}

func TestToolCallBlockDifferentThemes(t *testing.T) {
	data := ToolCallData{
		Name:   "bash",
		Status: ToolRunning,
	}
	dark := ToolCallBlock(testContext(theme.DarkTheme(), 80), data)
	light := ToolCallBlock(testContext(theme.LightTheme(), 80), data)
	if dark == light {
		t.Error("dark and light themes should produce different output")
	}
}
