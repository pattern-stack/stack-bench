package molecules

import (
	"strings"
	"testing"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

func TestHeader_ContainsTitle(t *testing.T) {
	out := Header(darkCtx(), HeaderData{
		Title: "My Page",
	})
	if !strings.Contains(out, "My Page") {
		t.Error("expected header to contain the title")
	}
}

func TestHeader_ContainsSeparator(t *testing.T) {
	out := Header(darkCtx(), HeaderData{
		Title: "Title",
	})
	if !strings.Contains(out, "─") {
		t.Error("expected header to contain a separator line")
	}
}

func TestHeader_ContainsBadges(t *testing.T) {
	out := Header(darkCtx(), HeaderData{
		Title: "Dashboard",
		Badges: []atoms.BadgeData{
			{Label: "v1.0", Style: theme.Style{Category: theme.CatAgent}, Variant: atoms.BadgeOutline},
			{Label: "beta", Style: theme.Style{Status: theme.Warning}, Variant: atoms.BadgeFilled},
		},
	})
	if !strings.Contains(out, "v1.0") {
		t.Error("expected header to contain first badge")
	}
	if !strings.Contains(out, "beta") {
		t.Error("expected header to contain second badge")
	}
}

func TestHeader_NoBadges(t *testing.T) {
	out := Header(darkCtx(), HeaderData{
		Title: "Simple",
	})
	lines := strings.Split(out, "\n")
	if len(lines) < 2 {
		t.Fatal("expected at least two lines (title + separator)")
	}
}

func TestHeader_LightTheme(t *testing.T) {
	out := Header(lightCtx(), HeaderData{
		Title: "Light Header",
	})
	if !strings.Contains(out, "Light Header") {
		t.Error("expected light theme header to contain title")
	}
	if !strings.Contains(out, "─") {
		t.Error("expected light theme header to contain separator")
	}
}
