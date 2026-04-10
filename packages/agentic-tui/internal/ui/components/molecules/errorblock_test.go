package molecules

import (
	"strings"
	"testing"
)

func TestErrorBlock_ContainsBadge(t *testing.T) {
	out := ErrorBlock(darkCtx(), ErrorBlockData{
		Message: "something went wrong",
	})
	if !strings.Contains(out, "error") {
		t.Error("expected error block to contain 'error' badge")
	}
}

func TestErrorBlock_ContainsMessage(t *testing.T) {
	out := ErrorBlock(darkCtx(), ErrorBlockData{
		Message: "connection refused",
	})
	if !strings.Contains(out, "connection refused") {
		t.Error("expected error block to contain the error message")
	}
}

func TestErrorBlock_CustomTitle(t *testing.T) {
	out := ErrorBlock(darkCtx(), ErrorBlockData{
		Title:   "fatal",
		Message: "disk full",
	})
	if !strings.Contains(out, "fatal") {
		t.Error("expected error block to contain custom title")
	}
}

func TestErrorBlock_WithSuggestions(t *testing.T) {
	out := ErrorBlock(darkCtx(), ErrorBlockData{
		Message:     "file not found",
		Suggestions: []string{"check the path", "verify permissions"},
	})
	if !strings.Contains(out, "check the path") {
		t.Error("expected error block to contain first suggestion")
	}
	if !strings.Contains(out, "verify permissions") {
		t.Error("expected error block to contain second suggestion")
	}
}

func TestErrorBlock_WithoutSuggestions(t *testing.T) {
	out := ErrorBlock(darkCtx(), ErrorBlockData{
		Message: "unknown error",
	})
	// Should still render without errors
	if !strings.Contains(out, "unknown error") {
		t.Error("expected error block to contain message without suggestions")
	}
	// Should not contain suggestion markers
	if strings.Contains(out, "  - ") {
		t.Error("expected no suggestion bullet points when suggestions are empty")
	}
}

func TestErrorBlock_LightTheme(t *testing.T) {
	out := ErrorBlock(lightCtx(), ErrorBlockData{
		Message:     "timeout",
		Suggestions: []string{"retry later"},
	})
	if !strings.Contains(out, "error") {
		t.Error("expected light theme error block to contain badge")
	}
	if !strings.Contains(out, "timeout") {
		t.Error("expected light theme error block to contain message")
	}
}
