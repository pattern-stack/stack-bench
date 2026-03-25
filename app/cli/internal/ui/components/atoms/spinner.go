package atoms

import (
	"time"

	tea "charm.land/bubbletea/v2"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// spinnerFrames is the braille dot animation sequence.
var spinnerFrames = []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}

// spinnerInterval is the time between frame advances.
const spinnerInterval = 80 * time.Millisecond

// spinnerSeq is a package-level counter for unique Spinner IDs.
var spinnerSeq int

// TickMsg is sent by the Spinner's tick command.
// ID scopes ticks to a specific Spinner instance.
type TickMsg struct {
	ID int
}

// Spinner is an animated braille indicator.
// It follows the Bubble Tea sub-model pattern (like chat.Model):
// Update returns (Spinner, tea.Cmd) rather than (tea.Model, tea.Cmd).
type Spinner struct {
	id    int
	frame int
	Style theme.Style
}

// NewSpinner creates a Spinner with the default Running style.
func NewSpinner() Spinner {
	spinnerSeq++
	return Spinner{
		id:    spinnerSeq,
		Style: theme.Style{Status: theme.Running},
	}
}

// Init returns the first tick command.
func (s Spinner) Init() tea.Cmd {
	return s.tick()
}

// Update advances the frame on a matching TickMsg.
func (s Spinner) Update(msg tea.Msg) (Spinner, tea.Cmd) {
	if msg, ok := msg.(TickMsg); ok && msg.ID == s.id {
		s.frame = (s.frame + 1) % len(spinnerFrames)
		return s, s.tick()
	}
	return s, nil
}

// ViewWith renders the current frame glyph using the given RenderContext.
// This is the primary render method, used by molecule composition.
func (s Spinner) ViewWith(ctx RenderContext) string {
	style := ctx.Theme.Resolve(s.Style)
	return style.Render(spinnerFrames[s.frame])
}

// View renders the current frame using the active theme.
// Convenience for standalone usage outside a molecule.
func (s Spinner) View() string {
	style := theme.Resolve(s.Style)
	return style.Render(spinnerFrames[s.frame])
}

// tick returns a tea.Cmd that sends a TickMsg after the interval.
func (s Spinner) tick() tea.Cmd {
	id := s.id
	return tea.Tick(spinnerInterval, func(time.Time) tea.Msg {
		return TickMsg{ID: id}
	})
}
