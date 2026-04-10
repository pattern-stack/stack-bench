package app

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"

	"github.com/dugshub/agentic-tui/internal/ui/components/atoms"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

// spinnerEntry pairs a labeled spinner with its description for the gallery.
type spinnerEntry struct {
	name        string
	description string
	spinner     atoms.Spinner
}

// SpinnerGallery is a Bubble Tea model that displays every available spinner
// preset side-by-side, animated independently. Press q or esc to exit.
type SpinnerGallery struct {
	entries []spinnerEntry
	width   int
	height  int
}

// NewSpinnerGallery constructs a gallery containing every preset.
func NewSpinnerGallery() SpinnerGallery {
	style := theme.Style{Status: theme.Running}

	mk := func(id int, frames []string) atoms.Spinner {
		s := atoms.NewSpinner(id, style)
		s.Frames = frames
		return s
	}

	entries := []spinnerEntry{
		{"Dense", "current default — fills cell, baseline-aligned", mk(1, atoms.SpinnerDense)},
		{"Sparse", "classic top-dot braille — light, floats high", mk(2, atoms.SpinnerSparse)},
		{"SparseLow", "sparse rotation shifted down — sits on baseline", mk(3, atoms.SpinnerSparseLow)},
		{"SparseCenter", "2x2 centered — stays in the middle rows", mk(4, atoms.SpinnerSparseCenter)},
		{"Pulse", "centered 2x2 breathing — inhale/exhale", mk(5, atoms.SpinnerPulse)},
		{"Heartbeat", "lub-dub rhythm — two beats then rest", mk(6, atoms.SpinnerHeartbeat)},
		{"Twinkle", "growing/shrinking star — smoother Star variant", mk(7, atoms.SpinnerTwinkle)},
		{"Bounce", "single dot ping-ponging vertically", mk(8, atoms.SpinnerBounce)},
		{"Pong", "ball bouncing between paddles (6 cells)", mk(9, atoms.SpinnerPong)},
		{"Orbit", "single dot tracing the perimeter — minimal", mk(10, atoms.SpinnerOrbit)},
		{"Arc", "rotating quarter-circle — smooth", mk(11, atoms.SpinnerArc)},
		{"HalfCircle", "filled half rotating — chunky", mk(12, atoms.SpinnerHalfCircle)},
		{"Star", "pulsing six-point star — sparkly", mk(13, atoms.SpinnerStar)},
		{"Arrow", "compass arrow rotating", mk(14, atoms.SpinnerArrow)},
		{"Triangle", "filled triangle rotating", mk(15, atoms.SpinnerTriangle)},
		{"PulseBar", "vertical bar growing/shrinking", mk(16, atoms.SpinnerPulseBar)},
		{"BlockFade", "block fading in and out", mk(17, atoms.SpinnerBlockFade)},
		{"Classic", "ASCII pipe spinner — terminal-safe", mk(18, atoms.SpinnerClassic)},
	}

	return SpinnerGallery{entries: entries}
}

// Init starts every spinner's tick loop.
func (g SpinnerGallery) Init() tea.Cmd {
	cmds := make([]tea.Cmd, 0, len(g.entries))
	for _, e := range g.entries {
		cmds = append(cmds, e.spinner.Init())
	}
	return tea.Batch(cmds...)
}

// Update routes tick messages to the matching spinner and handles quit keys.
func (g SpinnerGallery) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyPressMsg:
		switch msg.String() {
		case "q", "esc", "ctrl+c":
			return g, tea.Quit
		}
	case tea.WindowSizeMsg:
		g.width = msg.Width
		g.height = msg.Height
	case atoms.SpinnerTickMsg:
		var cmds []tea.Cmd
		for i := range g.entries {
			updated, cmd := g.entries[i].spinner.Update(msg)
			g.entries[i].spinner = updated
			if cmd != nil {
				cmds = append(cmds, cmd)
			}
		}
		return g, tea.Batch(cmds...)
	}
	return g, nil
}

// View renders the gallery as a table: spinner | name | description.
func (g SpinnerGallery) View() tea.View {
	return tea.NewView(g.render())
}

// render produces the textual body of the gallery.
func (g SpinnerGallery) render() string {
	width := g.width
	if width <= 0 {
		width = 80
	}
	ctx := atoms.DefaultContext(width)
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	var sb strings.Builder
	sb.WriteString("\n")
	sb.WriteString("  Spinner Gallery — press q or esc to exit\n\n")

	// Find the longest name for alignment.
	maxName := 0
	for _, e := range g.entries {
		if len(e.name) > maxName {
			maxName = len(e.name)
		}
	}

	for _, e := range g.entries {
		spinner := e.spinner.View(inlineCtx)
		name := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  fmt.Sprintf("%-*s", maxName, e.name),
			Style: theme.Style{Hierarchy: theme.Secondary},
		})
		desc := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  e.description,
			Style: theme.Style{Hierarchy: theme.Tertiary},
		})
		sb.WriteString("    " + spinner + "  " + name + "  " + desc + "\n\n")
	}

	sb.WriteString("\n")
	return sb.String()
}
