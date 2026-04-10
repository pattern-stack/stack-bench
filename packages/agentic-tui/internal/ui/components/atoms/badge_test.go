package atoms

import (
	"strings"
	"testing"

	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

func TestBadgeFilledRenders(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := BadgeData{
		Label:   "user",
		Style:   theme.Style{Category: theme.CatUser},
		Variant: BadgeFilled,
	}

	result := Badge(ctx, data)
	if result == "" {
		t.Error("Badge(Filled) returned empty string")
	}
	if !strings.Contains(result, "user") {
		t.Error("Badge should contain the label text")
	}
}

func TestBadgeOutlineRenders(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := BadgeData{
		Label:   "system",
		Style:   theme.Style{Category: theme.CatSystem},
		Variant: BadgeOutline,
	}

	result := Badge(ctx, data)
	if result == "" {
		t.Error("Badge(Outline) returned empty string")
	}
	if !strings.Contains(result, "[") || !strings.Contains(result, "]") {
		t.Error("Outline badge should contain brackets")
	}
	if !strings.Contains(result, "system") {
		t.Error("Badge should contain the label text")
	}
}

func TestBadgeVariantsProduceDifferentOutput(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	style := theme.Style{Category: theme.CatAgent}

	filled := Badge(ctx, BadgeData{Label: "test", Style: style, Variant: BadgeFilled})
	outline := Badge(ctx, BadgeData{Label: "test", Style: style, Variant: BadgeOutline})

	if filled == outline {
		t.Error("Filled and Outline variants should produce structurally different output")
	}
}

func TestBadgeTruncation(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := BadgeData{
		Label:    "this is a very long label that exceeds the limit",
		Style:    theme.Style{},
		Variant:  BadgeOutline,
		MaxWidth: 10,
	}

	result := Badge(ctx, data)
	// The label should be truncated -- check for ellipsis character
	if !strings.Contains(result, "\u2026") {
		t.Error("long label should be truncated with ellipsis")
	}
}

func TestBadgeDefaultTruncation(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := BadgeData{
		Label:   "this is a label longer than sixteen chars",
		Style:   theme.Style{},
		Variant: BadgeOutline,
	}

	result := Badge(ctx, data)
	if !strings.Contains(result, "\u2026") {
		t.Error("label exceeding default max width (16) should be truncated")
	}
}

func TestBadgeDifferentThemes(t *testing.T) {
	data := BadgeData{
		Label:   "test",
		Style:   theme.Style{Category: theme.CatAgent},
		Variant: BadgeFilled,
	}

	dark := Badge(testContext(theme.DarkTheme(), 80), data)
	light := Badge(testContext(theme.LightTheme(), 80), data)

	if dark == light {
		t.Error("expected different output for dark vs light themes")
	}
}

func TestBadgeShortLabelNotTruncated(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := BadgeData{
		Label:   "ok",
		Style:   theme.Style{},
		Variant: BadgeOutline,
	}

	result := Badge(ctx, data)
	if strings.Contains(result, "\u2026") {
		t.Error("short label should not be truncated")
	}
	if !strings.Contains(result, "ok") {
		t.Error("short label should appear in full")
	}
}
