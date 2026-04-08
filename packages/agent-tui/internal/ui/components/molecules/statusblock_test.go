package molecules

import (
	"strings"
	"testing"

	"github.com/dugshub/agent-tui/internal/ui/components/atoms"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

func testContext(t *theme.Theme, width int) atoms.RenderContext {
	return atoms.RenderContext{Width: width, Theme: t}
}

func TestStatusBlock_ContainsVerb(t *testing.T) {
	s := atoms.NewSpinner(1, theme.Style{Status: theme.Running})
	out := StatusBlock(darkCtx(), StatusBlockData{
		Spinner: s,
		Verb:    "Reading",
	})
	if !strings.Contains(out, "Reading") {
		t.Error("expected status block to contain verb")
	}
}

func TestStatusBlock_ContainsSpinnerFrame(t *testing.T) {
	s := atoms.NewSpinner(1, theme.Style{Status: theme.Running})
	out := StatusBlock(darkCtx(), StatusBlockData{
		Spinner: s,
		Verb:    "Loading",
	})
	if !strings.Contains(out, atoms.SpinnerFrames[0]) {
		t.Error("expected status block to contain spinner frame")
	}
}

func TestStatusBlock_WithElapsed(t *testing.T) {
	s := atoms.NewSpinner(1, theme.Style{Status: theme.Running})
	out := StatusBlock(darkCtx(), StatusBlockData{
		Spinner: s,
		Verb:    "Building",
		Elapsed: 3.2,
	})
	if !strings.Contains(out, "3.2s") {
		t.Error("expected status block to contain elapsed time")
	}
}

func TestStatusBlock_WithCount(t *testing.T) {
	s := atoms.NewSpinner(1, theme.Style{Status: theme.Running})
	out := StatusBlock(darkCtx(), StatusBlockData{
		Spinner: s,
		Verb:    "Processing",
		Count:   12,
		Unit:    "files",
	})
	if !strings.Contains(out, "12 files") {
		t.Error("expected status block to contain count and unit")
	}
}

func TestStatusBlock_WithBothOptionals(t *testing.T) {
	s := atoms.NewSpinner(1, theme.Style{Status: theme.Running})
	out := StatusBlock(darkCtx(), StatusBlockData{
		Spinner: s,
		Verb:    "Scanning",
		Elapsed: 1.5,
		Count:   5,
		Unit:    "dirs",
	})
	if !strings.Contains(out, "1.5s") {
		t.Error("expected elapsed badge")
	}
	if !strings.Contains(out, "5 dirs") {
		t.Error("expected count badge")
	}
}

func TestStatusBlock_LightTheme(t *testing.T) {
	s := atoms.NewSpinner(1, theme.Style{Status: theme.Running})
	out := StatusBlock(lightCtx(), StatusBlockData{
		Spinner: s,
		Verb:    "Indexing",
		Elapsed: 2.0,
	})
	if !strings.Contains(out, "Indexing") {
		t.Error("expected light theme status block to contain verb")
	}
}
