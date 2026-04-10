package atoms

import (
	"strings"
	"testing"

	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

func TestIconGlyphs(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	style := theme.Style{}

	tests := []struct {
		name     IconName
		expected string
	}{
		{IconCursor, ">"},
		{IconArrow, "\u2192"},
		{IconBullet, "\u2022"},
		{IconCheck, "\u2713"},
		{IconX, "\u2717"},
		{IconDot, "\u25CF"},
		{IconCircle, "\u25CB"},
		{IconWarning, "\u26A0"},
		{IconInfo, "\u2139"},
	}

	for _, tt := range tests {
		result := Icon(ctx, tt.name, style)
		if !strings.Contains(result, tt.expected) {
			t.Errorf("Icon(%d) = %q, expected to contain %q", tt.name, result, tt.expected)
		}
	}
}

func TestIconUnknownReturnsEmpty(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := Icon(ctx, IconName(999), theme.Style{})
	if result != "" {
		t.Errorf("unknown icon should return empty string, got %q", result)
	}
}

func TestIconDifferentThemes(t *testing.T) {
	style := theme.Style{Category: theme.CatAgent}

	dark := Icon(testContext(theme.DarkTheme(), 80), IconCheck, style)
	light := Icon(testContext(theme.LightTheme(), 80), IconCheck, style)

	if dark == light {
		t.Error("expected different output for dark vs light themes")
	}
}

func TestIconNoNewlines(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	for _, name := range []IconName{IconCursor, IconArrow, IconBullet, IconCheck, IconX, IconDot, IconCircle, IconWarning, IconInfo} {
		result := Icon(ctx, name, theme.Style{})
		if strings.Contains(result, "\n") {
			t.Errorf("Icon(%d) should not contain newlines", name)
		}
	}
}
