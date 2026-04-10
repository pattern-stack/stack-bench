package atoms

import (
	"strings"
	"testing"

	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

func TestSeparatorRenders(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 40)
	result := Separator(ctx)
	if result == "" {
		t.Error("Separator returned empty string")
	}
	// Should contain the box-drawing horizontal line character
	if !strings.Contains(result, "\u2500") {
		t.Error("Separator should contain box-drawing character \u2500")
	}
}

func TestSeparatorRespectsWidth(t *testing.T) {
	narrow := Separator(testContext(theme.DarkTheme(), 10))
	wide := Separator(testContext(theme.DarkTheme(), 40))

	// Wider separator should produce longer output
	if len(wide) <= len(narrow) {
		t.Error("wider separator should produce longer output")
	}
}

func TestSeparatorDifferentThemes(t *testing.T) {
	dark := Separator(testContext(theme.DarkTheme(), 40))
	light := Separator(testContext(theme.LightTheme(), 40))

	if dark == light {
		t.Error("expected different output for dark vs light themes")
	}
}

func TestSeparatorNoNewlines(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 40)
	result := Separator(ctx)
	if strings.Contains(result, "\n") {
		t.Error("Separator should be a single line")
	}
}
