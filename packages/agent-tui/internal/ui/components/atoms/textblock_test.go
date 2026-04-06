package atoms

import (
	"testing"

	"github.com/dugshub/agent-tui/internal/ui/theme"
)

func TestTextBlockRenders(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 40)
	data := TextBlockData{
		Text:  "hello world",
		Style: theme.Style{},
	}

	result := TextBlock(ctx, data)
	if result == "" {
		t.Error("TextBlock returned empty string")
	}
	if len(result) < len("hello world") {
		t.Errorf("TextBlock output too short: %q", result)
	}
}

func TestTextBlockDifferentThemes(t *testing.T) {
	style := theme.Style{Category: theme.CatAgent}
	data := TextBlockData{Text: "test", Style: style}

	dark := TextBlock(testContext(theme.DarkTheme(), 40), data)
	light := TextBlock(testContext(theme.LightTheme(), 40), data)

	if dark == light {
		t.Error("expected different output for dark vs light themes")
	}
}

func TestTextBlockRespectsWidth(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 10)
	data := TextBlockData{
		Text:  "short",
		Style: theme.Style{},
	}

	result := TextBlock(ctx, data)
	if result == "" {
		t.Error("TextBlock returned empty string for narrow width")
	}
}
