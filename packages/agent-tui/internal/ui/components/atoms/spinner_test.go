package atoms

import (
	"strings"
	"testing"

	"github.com/dugshub/agent-tui/internal/ui/theme"
)

func TestSpinner_InitialFrame(t *testing.T) {
	s := NewSpinner(1, theme.Style{Status: theme.Running})
	ctx := testContext(theme.DarkTheme(), 80)

	out := s.View(ctx)
	if !strings.Contains(out, SpinnerFrames[0]) {
		t.Error("initial frame should be the first braille character")
	}
}

func TestSpinner_AdvancesOnTick(t *testing.T) {
	s := NewSpinner(1, theme.Style{Status: theme.Running})
	ctx := testContext(theme.DarkTheme(), 80)

	s, _ = s.Update(SpinnerTickMsg{ID: 1})
	out := s.View(ctx)
	if !strings.Contains(out, SpinnerFrames[1]) {
		t.Error("spinner should advance to second frame after one tick")
	}
}

func TestSpinner_IgnoresOtherIDs(t *testing.T) {
	s := NewSpinner(1, theme.Style{Status: theme.Running})
	ctx := testContext(theme.DarkTheme(), 80)

	before := s.View(ctx)
	s, _ = s.Update(SpinnerTickMsg{ID: 99})
	after := s.View(ctx)

	if before != after {
		t.Error("spinner should ignore ticks for other IDs")
	}
}

func TestSpinner_Wraps(t *testing.T) {
	s := NewSpinner(1, theme.Style{Status: theme.Running})
	ctx := testContext(theme.DarkTheme(), 80)

	for i := 0; i < len(SpinnerFrames); i++ {
		s, _ = s.Update(SpinnerTickMsg{ID: 1})
	}

	out := s.View(ctx)
	if !strings.Contains(out, SpinnerFrames[0]) {
		t.Error("spinner should wrap back to first frame")
	}
}

func TestSpinner_InitReturnsCmd(t *testing.T) {
	s := NewSpinner(1, theme.Style{Status: theme.Running})
	cmd := s.Init()
	if cmd == nil {
		t.Error("Init should return a tick command")
	}
}

func TestSpinner_UpdateReturnsCmdOnMatch(t *testing.T) {
	s := NewSpinner(1, theme.Style{Status: theme.Running})
	_, cmd := s.Update(SpinnerTickMsg{ID: 1})
	if cmd == nil {
		t.Error("Update should return a tick command on matching ID")
	}
}

func TestSpinner_UpdateReturnsNilOnMismatch(t *testing.T) {
	s := NewSpinner(1, theme.Style{Status: theme.Running})
	_, cmd := s.Update(SpinnerTickMsg{ID: 99})
	if cmd != nil {
		t.Error("Update should return nil command on mismatched ID")
	}
}
