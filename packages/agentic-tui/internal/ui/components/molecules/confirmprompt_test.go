package molecules

import (
	"strings"
	"testing"
)

func TestConfirmPrompt_ContainsQuestion(t *testing.T) {
	out := ConfirmPrompt(darkCtx(), ConfirmPromptData{
		Question: "Continue?",
		Selected: true,
	})
	if !strings.Contains(out, "Continue?") {
		t.Error("expected confirm prompt to contain question text")
	}
}

func TestConfirmPrompt_ContainsYes(t *testing.T) {
	out := ConfirmPrompt(darkCtx(), ConfirmPromptData{
		Question: "Save?",
		Selected: true,
	})
	if !strings.Contains(out, "yes") {
		t.Error("expected confirm prompt to contain 'yes'")
	}
}

func TestConfirmPrompt_ContainsNo(t *testing.T) {
	out := ConfirmPrompt(darkCtx(), ConfirmPromptData{
		Question: "Save?",
		Selected: false,
	})
	if !strings.Contains(out, "no") {
		t.Error("expected confirm prompt to contain 'no'")
	}
}

func TestConfirmPrompt_SelectedYesDiffersFromNo(t *testing.T) {
	yes := ConfirmPrompt(darkCtx(), ConfirmPromptData{
		Question: "Delete?",
		Selected: true,
	})
	no := ConfirmPrompt(darkCtx(), ConfirmPromptData{
		Question: "Delete?",
		Selected: false,
	})
	if yes == no {
		t.Error("expected yes-selected and no-selected to render differently")
	}
}

func TestConfirmPrompt_LightTheme(t *testing.T) {
	out := ConfirmPrompt(lightCtx(), ConfirmPromptData{
		Question: "Proceed?",
		Selected: true,
	})
	if !strings.Contains(out, "Proceed?") {
		t.Error("expected light theme confirm prompt to contain question")
	}
	if !strings.Contains(out, "yes") {
		t.Error("expected light theme confirm prompt to contain 'yes'")
	}
}
