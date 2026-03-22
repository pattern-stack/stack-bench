package atoms

import (
	"strings"
	"testing"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

func TestInlineCodeRenders(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := InlineCode(ctx, "myVar")
	if result == "" {
		t.Error("InlineCode returned empty string")
	}
	if strings.Contains(result, "\n") {
		t.Error("InlineCode should not contain newlines")
	}
}

func TestInlineCodeDifferentThemes(t *testing.T) {
	dark := InlineCode(testContext(theme.DarkTheme(), 80), "code")
	light := InlineCode(testContext(theme.LightTheme(), 80), "code")

	if dark == light {
		t.Error("expected different output for dark vs light themes")
	}
}

func TestInlineCodePreservesContent(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := InlineCode(ctx, "fmt.Println")
	if !strings.Contains(result, "fmt.Println") {
		t.Error("InlineCode should contain the original code text")
	}
}
