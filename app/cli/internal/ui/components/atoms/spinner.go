package atoms

import (
	"time"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// Spinner frame presets. Each is a slice of single-cell glyphs that render
// in sequence to form an animation. Pick whichever fits the surrounding UI:
// dense braille for status icons, arc for elegant motion, classic for
// terminals without good unicode support.
var (
	// SpinnerDense is the dense 6/7-dot braille spinner. Every frame fills
	// the full cell so the spinner sits on the text baseline.
	SpinnerDense = []string{"⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"}

	// SpinnerSparse is the classic top-dot braille spinner. Lighter visual
	// weight; floats slightly above the baseline.
	SpinnerSparse = []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}

	// SpinnerSparseLow is the same rotation pattern as Sparse but shifted
	// down by one braille row, so it sits in the lower 3/4 of the cell.
	// Visually grounded against the text baseline rather than floating above.
	SpinnerSparseLow = []string{"⠖", "⠲", "⢲", "⢰", "⣰", "⣠", "⣄", "⣆", "⡆", "⡖"}

	// SpinnerSparseCenter is a 3-dot rotation that stays strictly within
	// rows 2 and 3 of the braille cell — a 2x2 square in the vertical
	// middle. Truly centered (unlike Sparse which floats high and
	// SparseLow which sits low), at the cost of only 4 frames.
	SpinnerSparseCenter = []string{"⠖", "⠲", "⠴", "⠦"}

	// SpinnerOrbit traces a single dot around the perimeter of the cell.
	SpinnerOrbit = []string{"⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"}

	// SpinnerArc rotates a quarter-circle arc.
	SpinnerArc = []string{"◜", "◠", "◝", "◞", "◡", "◟"}

	// SpinnerHalfCircle rotates a filled half-circle.
	SpinnerHalfCircle = []string{"◐", "◓", "◑", "◒"}

	// SpinnerStar pulses a six-pointed star.
	SpinnerStar = []string{"✶", "✸", "✹", "✺", "✹", "✷"}

	// SpinnerArrow rotates a compass-style arrow.
	SpinnerArrow = []string{"←", "↖", "↑", "↗", "→", "↘", "↓", "↙"}

	// SpinnerTriangle rotates a filled triangle.
	SpinnerTriangle = []string{"◢", "◣", "◤", "◥"}

	// SpinnerPulseBar grows and shrinks a vertical bar.
	SpinnerPulseBar = []string{"▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂"}

	// SpinnerBlockFade fades a block in and out.
	SpinnerBlockFade = []string{"░", "▒", "▓", "█", "▓", "▒", "░"}

	// SpinnerClassic is the retro ASCII spinner. Safe for any terminal.
	SpinnerClassic = []string{"|", "/", "-", "\\"}

	// SpinnerPulse is a centered "breathing" pattern that grows from empty
	// to a full 2x2 and shrinks back, all within rows 2-3 of the cell.
	// Calm, meditative, baseline-aligned.
	SpinnerPulse = []string{"⠀", "⠂", "⠒", "⠶", "⠒", "⠂"}

	// SpinnerHeartbeat mimics a lub-dub rhythm — two fast beats followed
	// by a longer rest. Centered in the middle of the cell.
	SpinnerHeartbeat = []string{"⠶", "⠂", "⠶", "⠂", "⠀", "⠀", "⠀", "⠀"}

	// SpinnerTwinkle is a star that grows and shrinks through several
	// sizes and point counts. Like Star with a wider size range, so the
	// animation reads as a "twinkle" rather than a pulse.
	SpinnerTwinkle = []string{"·", "✦", "✶", "✸", "✹", "✸", "✶", "✦"}

	// SpinnerBounce moves a single dot vertically through all 4 rows of
	// the braille cell (top → bottom → top). Minimal, baseline-spanning.
	SpinnerBounce = []string{"⠁", "⠂", "⠄", "⡀", "⠄", "⠂"}

	// SpinnerPong bounces a small ball between two half-block paddles.
	// Takes 6 cells of horizontal space — use in contexts where that fits.
	SpinnerPong = []string{
		"▌·   ▐",
		"▌ ·  ▐",
		"▌  · ▐",
		"▌   ·▐",
		"▌  · ▐",
		"▌ ·  ▐",
	}
)

// SpinnerFrames is the default frame set used when a Spinner has no Frames
// configured. Kept for backward compatibility with existing call sites.
var SpinnerFrames = SpinnerDense

// SpinnerInterval is the default tick duration between frames.
const SpinnerInterval = 80 * time.Millisecond

// SpinnerTickMsg signals the spinner to advance one frame.
type SpinnerTickMsg struct {
	ID int // identifies which spinner instance this tick belongs to
}

// Spinner is a Bubble Tea model that renders an animated indicator. The
// frames and tick interval are per-instance so different spinners can use
// different visual styles in the same UI.
type Spinner struct {
	Style    theme.Style
	ID       int           // unique ID to filter ticks in a multi-spinner layout
	Frames   []string      // animation frames; defaults to SpinnerFrames if empty
	Interval time.Duration // tick interval; defaults to SpinnerInterval if zero
	frame    int
}

// NewSpinner creates a Spinner with the given style and unique ID. Frames
// and interval default to package-level values.
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
		frames := s.frames()
		s.frame = (s.frame + 1) % len(frames)
		return s, s.tick()
	}
	return s, nil
}

// View renders the current frame with the resolved style.
func (s Spinner) View(ctx RenderContext) string {
	resolved := ctx.Theme.Resolve(s.Style)
	frames := s.frames()
	if len(frames) == 0 {
		return ""
	}
	return resolved.Render(frames[s.frame%len(frames)])
}

// frames returns the configured frames or the package default.
func (s Spinner) frames() []string {
	if len(s.Frames) > 0 {
		return s.Frames
	}
	return SpinnerFrames
}

// interval returns the configured interval or the package default.
func (s Spinner) interval() time.Duration {
	if s.Interval > 0 {
		return s.Interval
	}
	return SpinnerInterval
}

// tick returns a tea.Cmd that sends a SpinnerTickMsg after the interval.
func (s Spinner) tick() tea.Cmd {
	id := s.ID
	return tea.Tick(s.interval(), func(time.Time) tea.Msg {
		return SpinnerTickMsg{ID: id}
	})
}
