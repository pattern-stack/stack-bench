package atoms

import (
	"strings"
	"testing"

	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

func TestHighlightCodeGoKeywordsVsStrings(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	code := `func main() {
	fmt.Println("hello")
}`
	result := HighlightCode(ctx, code, "go")

	// The result should contain ANSI escape sequences (styled output)
	if !strings.Contains(result, "\x1b[") {
		t.Error("expected ANSI escape sequences in highlighted output")
	}
	// Should still contain the original text content
	if !strings.Contains(result, "func") {
		t.Error("expected 'func' keyword in output")
	}
	if !strings.Contains(result, "hello") {
		t.Error("expected string content in output")
	}
}

func TestHighlightCodeDifferentTokenStyles(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)

	// Highlight a snippet with keywords, strings, and comments
	code := `// a comment
var x = "hello"`
	result := HighlightCode(ctx, code, "go")

	// Plain unstyled version would have no ANSI codes
	plain := "// a comment\nvar x = \"hello\""
	if result == plain {
		t.Error("highlighted output should differ from plain text")
	}
}

func TestHighlightCodeUnknownLanguageFallback(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	code := "some random text"
	result := HighlightCode(ctx, code, "not-a-real-language-xyz")

	// Should return the code unchanged (no styling)
	if result != code {
		t.Errorf("expected plain fallback for unknown language, got %q", result)
	}
}

func TestHighlightCodeEmptyLanguageFallback(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	code := "some random text"
	result := HighlightCode(ctx, code, "")

	// Should return the code unchanged
	if result != code {
		t.Errorf("expected plain fallback for empty language, got %q", result)
	}
}

func TestHighlightCodeDarkVsLightTheme(t *testing.T) {
	code := `func hello() string {
	return "world"
}`
	dark := HighlightCode(testContext(theme.DarkTheme(), 80), code, "go")
	light := HighlightCode(testContext(theme.LightTheme(), 80), code, "go")

	if dark == light {
		t.Error("expected different output for dark vs light themes")
	}
	// Both should contain the source text
	if !strings.Contains(dark, "hello") || !strings.Contains(light, "hello") {
		t.Error("expected source text preserved in both themes")
	}
}

func TestHighlightCodePythonSupport(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	code := `def greet(name):
    return f"Hello, {name}"
`
	result := HighlightCode(ctx, code, "python")

	if !strings.Contains(result, "\x1b[") {
		t.Error("expected ANSI escape sequences for Python highlighting")
	}
	if !strings.Contains(result, "def") {
		t.Error("expected 'def' keyword in output")
	}
}

func TestHighlightCodeEmptyCode(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := HighlightCode(ctx, "", "go")

	// Empty code should not panic and should return empty or near-empty
	if strings.Contains(result, "func") {
		t.Error("empty code should not produce unexpected content")
	}
}
