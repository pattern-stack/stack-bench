package molecules

import (
	"strings"
	"testing"
)

func TestRadioSelect_ContainsLabel(t *testing.T) {
	out := RadioSelect(darkCtx(), RadioSelectData{
		Label: "Choose an agent:",
		Options: []RadioOption{
			{Label: "Alpha"},
			{Label: "Beta"},
		},
		Selected: 0,
	})
	if !strings.Contains(out, "Choose an agent:") {
		t.Error("expected radio select to contain label")
	}
}

func TestRadioSelect_ContainsOptions(t *testing.T) {
	out := RadioSelect(darkCtx(), RadioSelectData{
		Label: "Pick one:",
		Options: []RadioOption{
			{Label: "First"},
			{Label: "Second"},
			{Label: "Third"},
		},
		Selected: 1,
	})
	if !strings.Contains(out, "First") {
		t.Error("expected radio select to contain 'First'")
	}
	if !strings.Contains(out, "Second") {
		t.Error("expected radio select to contain 'Second'")
	}
}

func TestRadioSelect_SelectedCursor(t *testing.T) {
	out := RadioSelect(darkCtx(), RadioSelectData{
		Options: []RadioOption{
			{Label: "A"},
			{Label: "B"},
		},
		Selected: 0,
	})
	if !strings.Contains(out, ">") {
		t.Error("expected selected item to show cursor icon")
	}
}

func TestRadioSelect_DifferentSelections(t *testing.T) {
	opts := []RadioOption{
		{Label: "X"},
		{Label: "Y"},
	}
	sel0 := RadioSelect(darkCtx(), RadioSelectData{Options: opts, Selected: 0})
	sel1 := RadioSelect(darkCtx(), RadioSelectData{Options: opts, Selected: 1})
	if sel0 == sel1 {
		t.Error("expected different selections to produce different output")
	}
}

func TestRadioSelect_WithDescriptions(t *testing.T) {
	out := RadioSelect(darkCtx(), RadioSelectData{
		Options: []RadioOption{
			{Label: "Fast", Description: "Quick but less thorough"},
			{Label: "Thorough", Description: "Slow but complete"},
		},
		Selected: 0,
	})
	if !strings.Contains(out, "Quick but less thorough") {
		t.Error("expected radio select to contain first description")
	}
}

func TestRadioSelect_LightTheme(t *testing.T) {
	out := RadioSelect(lightCtx(), RadioSelectData{
		Label: "Theme:",
		Options: []RadioOption{
			{Label: "Dark"},
			{Label: "Light"},
		},
		Selected: 1,
	})
	if !strings.Contains(out, "Theme:") {
		t.Error("expected light theme radio select to contain label")
	}
}
