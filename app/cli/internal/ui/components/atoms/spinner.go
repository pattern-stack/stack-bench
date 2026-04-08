package atoms

import (
	"time"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// SpinnerFrames contains the braille animation sequence. Uses the dense
// 6-dot variant so every frame fills the full cell — keeps the spinner
// vertically aligned with adjacent glyphs like ✓ and ✗ that sit on the
// baseline. The sparser top-dot frames (⠋⠙⠹) appear to float above the
// text baseline, which looks misaligned next to other status icons.
var SpinnerFrames = []string{"⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"}

// SpinnerInterval is the default tick duration between frames.
const SpinnerInterval = 80 * time.Millisecond

// SpinnerTickMsg signals the spinner to advance one frame.
type SpinnerTickMsg struct {
	ID int // identifies which spinner instance this tick belongs to
}

// Spinner is a Bubble Tea model that renders an animated braille indicator.
type Spinner struct {
	Style theme.Style
	ID    int // unique ID to filter ticks in a multi-spinner layout
	frame int
}

// NewSpinner creates a Spinner with the given style and unique ID.
func NewSpinner(id int, style theme.Style) Spinner {
	return Spinner{ID: id, Style: style}
}

// Init starts the tick loop.
func (s Spinner) Init() tea.Cmd {
	return s.tick()
}

// Update advances the frame on matching tick messages.
func (s Spinner) Update(msg tea.Msg) (Spinner, tea.Cmd) {
	if tick, ok := msg.(SpinnerTickMsg); ok && tick.ID == s.ID {
		s.frame = (s.frame + 1) % len(SpinnerFrames)
		return s, s.tick()
	}
	return s, nil
}

// View renders the current frame with the resolved style.
func (s Spinner) View(ctx RenderContext) string {
	resolved := ctx.Theme.Resolve(s.Style)
	return resolved.Render(SpinnerFrames[s.frame])
}

// tick returns a tea.Cmd that sends a SpinnerTickMsg after the interval.
func (s Spinner) tick() tea.Cmd {
	id := s.ID
	return tea.Tick(SpinnerInterval, func(time.Time) tea.Msg {
		return SpinnerTickMsg{ID: id}
	})
}
