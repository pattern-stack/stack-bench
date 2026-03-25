package molecules

import (
	"strings"
	"testing"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

func testContext(t *theme.Theme, width int) RenderContext {
	return RenderContext{Width: width, Theme: t}
}

func TestNewStatusBlock(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{Verb: "Syncing"})
	if sb.Data.Verb != "Syncing" {
		t.Errorf("expected verb 'Syncing', got %q", sb.Data.Verb)
	}
}

func TestStatusBlockInitReturnsCmd(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{Verb: "Building"})
	cmd := sb.Init()
	if cmd == nil {
		t.Error("Init() should return spinner tick command")
	}
}

func TestStatusBlockUpdateForwardsTick(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{Verb: "Testing"})
	// Get the spinner's ID to send the right TickMsg
	// We need to trigger a tick -- Init() would schedule one,
	// but we can directly send the message
	msg := atoms.TickMsg{ID: 0} // will be ignored (wrong ID)
	sb2, cmd := sb.Update(msg)
	// The tick was for a different ID, so cmd should be nil
	_ = sb2
	if cmd != nil {
		t.Error("mismatched tick should produce nil cmd")
	}
}

func TestStatusBlockViewRendersVerb(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{Verb: "Syncing"})
	ctx := testContext(theme.DarkTheme(), 80)
	result := sb.View(ctx)
	if !strings.Contains(result, "Syncing") {
		t.Error("View should contain the verb text")
	}
}

func TestStatusBlockViewRendersSpinner(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{Verb: "Building"})
	ctx := testContext(theme.DarkTheme(), 80)
	result := sb.View(ctx)
	// Should contain a braille character (first frame)
	if !strings.Contains(result, "⠋") {
		t.Error("View should contain spinner braille glyph")
	}
}

func TestStatusBlockViewRendersElapsed(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{
		Verb:    "Syncing",
		Elapsed: "5s",
	})
	ctx := testContext(theme.DarkTheme(), 80)
	result := sb.View(ctx)
	if !strings.Contains(result, "5s") {
		t.Error("View should contain elapsed badge text")
	}
}

func TestStatusBlockViewOmitsElapsedWhenEmpty(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{Verb: "Syncing"})
	ctx := testContext(theme.DarkTheme(), 80)
	result := sb.View(ctx)
	// Should not contain bracket pairs beyond the spinner
	// (no empty badges)
	if strings.Contains(result, "[]") {
		t.Error("should not render empty badges")
	}
}

func TestStatusBlockViewRendersCount(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{
		Verb:  "Building",
		Count: "3/7",
	})
	ctx := testContext(theme.DarkTheme(), 80)
	result := sb.View(ctx)
	if !strings.Contains(result, "3/7") {
		t.Error("View should contain count badge text")
	}
}

func TestStatusBlockViewOmitsCountWhenEmpty(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{Verb: "Building"})
	ctx := testContext(theme.DarkTheme(), 80)
	result := sb.View(ctx)
	if strings.Contains(result, "/") {
		t.Error("should not contain count separator when count is empty")
	}
}

func TestStatusBlockCompactOmitsElapsed(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{
		Verb:    "Syncing",
		Elapsed: "5s",
	})
	ctx := testContext(theme.DarkTheme(), 50)
	result := sb.View(ctx)
	if strings.Contains(result, "5s") {
		t.Error("compact mode should omit elapsed badge")
	}
}

func TestStatusBlockCompactOmitsCount(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{
		Verb:  "Building",
		Count: "3/7",
	})
	ctx := testContext(theme.DarkTheme(), 50)
	result := sb.View(ctx)
	if strings.Contains(result, "3/7") {
		t.Error("compact mode should omit count badge")
	}
}

func TestStatusBlockCompactKeepsVerb(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{
		Verb:    "Syncing",
		Elapsed: "5s",
		Count:   "3/7",
	})
	ctx := testContext(theme.DarkTheme(), 50)
	result := sb.View(ctx)
	if !strings.Contains(result, "Syncing") {
		t.Error("compact mode should still contain verb text")
	}
}

func TestStatusBlockNormalShowsAll(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{
		Verb:    "Merging",
		Elapsed: "10s",
		Count:   "2/5",
	})
	ctx := testContext(theme.DarkTheme(), 80)
	result := sb.View(ctx)
	for _, want := range []string{"Merging", "10s", "2/5"} {
		if !strings.Contains(result, want) {
			t.Errorf("normal mode should contain %q", want)
		}
	}
}

func TestStatusBlockViewAllParts(t *testing.T) {
	sb := NewStatusBlock(StatusBlockData{
		Verb:    "Merging",
		Elapsed: "1m30s",
		Count:   "2/5",
	})
	ctx := testContext(theme.DarkTheme(), 80)
	result := sb.View(ctx)
	for _, want := range []string{"Merging", "1m30s", "2/5"} {
		if !strings.Contains(result, want) {
			t.Errorf("View should contain %q", want)
		}
	}
}
