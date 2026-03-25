package atoms

import (
	"strings"
	"testing"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

func TestNewSpinnerDistinctIDs(t *testing.T) {
	s1 := NewSpinner()
	s2 := NewSpinner()
	if s1.id == s2.id {
		t.Error("expected distinct spinner IDs")
	}
}

func TestSpinnerInitReturnsCmd(t *testing.T) {
	s := NewSpinner()
	cmd := s.Init()
	if cmd == nil {
		t.Error("Init() should return a non-nil tick command")
	}
}

func TestSpinnerUpdateAdvancesFrame(t *testing.T) {
	s := NewSpinner()
	initial := s.frame
	s, cmd := s.Update(TickMsg{ID: s.id})
	if s.frame != initial+1 {
		t.Errorf("expected frame %d, got %d", initial+1, s.frame)
	}
	if cmd == nil {
		t.Error("Update should return next tick command")
	}
}

func TestSpinnerUpdateIgnoresMismatchedTick(t *testing.T) {
	s := NewSpinner()
	initial := s.frame
	s, cmd := s.Update(TickMsg{ID: s.id + 999})
	if s.frame != initial {
		t.Error("frame should not advance for mismatched tick ID")
	}
	if cmd != nil {
		t.Error("should return nil cmd for mismatched tick")
	}
}

func TestSpinnerFrameWraps(t *testing.T) {
	s := NewSpinner()
	s.frame = len(spinnerFrames) - 1
	s, _ = s.Update(TickMsg{ID: s.id})
	if s.frame != 0 {
		t.Errorf("expected frame to wrap to 0, got %d", s.frame)
	}
}

func TestSpinnerViewWithRenders(t *testing.T) {
	s := NewSpinner()
	ctx := testContext(theme.DarkTheme(), 80)
	result := s.ViewWith(ctx)
	if result == "" {
		t.Error("ViewWith returned empty string")
	}
	if !strings.Contains(result, "⠋") {
		t.Error("ViewWith should contain the first braille frame")
	}
}

func TestSpinnerViewWithDifferentThemes(t *testing.T) {
	s := NewSpinner()
	dark := s.ViewWith(testContext(theme.DarkTheme(), 80))
	light := s.ViewWith(testContext(theme.LightTheme(), 80))
	if dark == light {
		t.Error("expected different output for dark vs light themes")
	}
}

func TestSpinnerViewRendersCurrentFrame(t *testing.T) {
	s := NewSpinner()
	s.frame = 3
	ctx := testContext(theme.DarkTheme(), 80)
	result := s.ViewWith(ctx)
	if !strings.Contains(result, spinnerFrames[3]) {
		t.Errorf("expected frame 3 glyph %q in output", spinnerFrames[3])
	}
}
