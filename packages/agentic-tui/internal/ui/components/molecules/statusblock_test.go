package molecules

import (
	"strings"
	"testing"

	"github.com/dugshub/agentic-tui/internal/ui/components/atoms"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

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

func TestStatusBlock_WithoutOptionals(t *testing.T) {
	s := atoms.NewSpinner(1, theme.Style{Status: theme.Running})
	withBadges := StatusBlock(darkCtx(), StatusBlockData{
		Spinner: s,
		Verb:    "Waiting",
		Elapsed: 5.0,
		Count:   10,
		Unit:    "items",
	})
	without := StatusBlock(darkCtx(), StatusBlockData{
		Spinner: s,
		Verb:    "Waiting",
	})
	if len(without) >= len(withBadges) {
		t.Error("expected output without optionals to be shorter than with badges")
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
	if !strings.Contains(out, "2.0s") {
		t.Error("expected light theme status block to contain elapsed")
	}
}
