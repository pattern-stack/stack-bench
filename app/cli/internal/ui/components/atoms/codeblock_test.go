package atoms

import (
	"strings"
	"testing"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

func TestCodeBlockBasic(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := CodeBlockData{
		Code:     "fmt.Println(\"hello\")",
		Language: "go",
	}

	result := CodeBlock(ctx, data)
	if result == "" {
		t.Error("CodeBlock returned empty string")
	}
	// Should contain the language label
	if !strings.Contains(result, "go") {
		t.Error("expected language label in output")
	}
}

func TestCodeBlockWithLineNumbers(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := CodeBlockData{
		Code:        "line1\nline2\nline3",
		Language:    "",
		LineNumbers: true,
	}

	result := CodeBlock(ctx, data)
	lines := strings.Split(result, "\n")
	// 3 code lines + blank above + blank below = 5
	if len(lines) != 5 {
		t.Errorf("expected 5 lines (3 code + 2 spacing), got %d", len(lines))
	}
	// Line numbers should appear in the output
	if !strings.Contains(result, "1") || !strings.Contains(result, "3") {
		t.Error("expected line numbers in output")
	}
}

func TestCodeBlockWithoutLineNumbers(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := CodeBlockData{
		Code:        "line1\nline2",
		Language:    "",
		LineNumbers: false,
	}

	result := CodeBlock(ctx, data)
	lines := strings.Split(result, "\n")
	// 2 code lines + blank above + blank below = 4
	if len(lines) != 4 {
		t.Errorf("expected 4 lines (2 code + 2 spacing), got %d", len(lines))
	}
}

func TestCodeBlockWithLanguageLabel(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := CodeBlockData{
		Code:     "x = 1",
		Language: "python",
	}

	result := CodeBlock(ctx, data)
	lines := strings.Split(result, "\n")
	// First line should be the language label, rest is code
	if len(lines) < 2 {
		t.Errorf("expected at least 2 lines (label + code), got %d", len(lines))
	}
}

func TestCodeBlockDifferentThemes(t *testing.T) {
	data := CodeBlockData{
		Code:     "hello",
		Language: "txt",
	}

	dark := CodeBlock(testContext(theme.DarkTheme(), 80), data)
	light := CodeBlock(testContext(theme.LightTheme(), 80), data)

	if dark == light {
		t.Error("expected different output for dark vs light themes")
	}
}
