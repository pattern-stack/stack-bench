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
	if !strings.Contains(out, "Third") {
		t.Error("expected radio select to contain 'Third'")
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
	// The selected item should have the cursor icon (>)
	if !strings.Contains(out, ">") {
		t.Error("expected selected item to show cursor icon")
	}
}

func TestRadioSelect_UnselectedCircle(t *testing.T) {
	out := RadioSelect(darkCtx(), RadioSelectData{
		Options: []RadioOption{
			{Label: "A"},
			{Label: "B"},
		},
		Selected: 0,
	})
	// Unselected items should have the circle icon
	if !strings.Contains(out, "○") {
		t.Error("expected unselected items to show circle icon")
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
	if !strings.Contains(out, "Slow but complete") {
		t.Error("expected radio select to contain second description")
	}
}

func TestRadioSelect_NoLabel(t *testing.T) {
	out := RadioSelect(darkCtx(), RadioSelectData{
		Options: []RadioOption{
			{Label: "Only"},
		},
		Selected: 0,
	})
	// Should render without crashing, contain the option
	if !strings.Contains(out, "Only") {
		t.Error("expected radio select without label to contain option")
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
	if !strings.Contains(out, "Dark") {
		t.Error("expected light theme radio select to contain 'Dark'")
	}
}
