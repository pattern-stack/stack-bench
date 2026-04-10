package molecules

import (
	"strings"
	"testing"

	"github.com/dugshub/agentic-tui/internal/ui/components/atoms"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

func darkCtx() atoms.RenderContext {
	return atoms.RenderContext{Theme: theme.DarkTheme(), Width: 80}
}

func lightCtx() atoms.RenderContext {
	return atoms.RenderContext{Theme: theme.LightTheme(), Width: 80}
}

func TestMessageBlock_UserRole(t *testing.T) {
	out := MessageBlock(darkCtx(), MessageBlockData{
		Role:    atoms.RoleUser,
		Content: "Hello world",
	})
	if !strings.Contains(out, "user") {
		t.Error("expected output to contain 'user' badge label")
	}
	if !strings.Contains(out, "Hello world") {
		t.Error("expected output to contain message content")
	}
}

func TestMessageBlock_AssistantRole(t *testing.T) {
	out := MessageBlock(darkCtx(), MessageBlockData{
		Role:    atoms.RoleAssistant,
		Content: "I can help with that.",
	})
	if !strings.Contains(out, "assistant") {
		t.Error("expected output to contain 'assistant' badge label")
	}
	if !strings.Contains(out, "I can help with that.") {
		t.Error("expected output to contain message content")
	}
}

func TestMessageBlock_SystemRole(t *testing.T) {
	out := MessageBlock(darkCtx(), MessageBlockData{
		Role:    atoms.RoleSystem,
		Content: "System prompt.",
	})
	if !strings.Contains(out, "system") {
		t.Error("expected output to contain 'system' badge label")
	}
	if !strings.Contains(out, "System prompt.") {
		t.Error("expected output to contain message content")
	}
}

func TestMessageBlock_ContentIndented(t *testing.T) {
	out := MessageBlock(darkCtx(), MessageBlockData{
		Role:    atoms.RoleUser,
		Content: "indented text",
	})
	lines := strings.Split(out, "\n")
	if len(lines) < 2 {
		t.Fatal("expected at least two lines (badge + content)")
	}
	// The content line should start with indentation
	if !strings.Contains(lines[1], "indented text") {
		t.Error("expected second line to contain the content")
	}
}

func TestMessageBlock_LightTheme(t *testing.T) {
	out := MessageBlock(lightCtx(), MessageBlockData{
		Role:    atoms.RoleAssistant,
		Content: "light mode",
	})
	if !strings.Contains(out, "assistant") {
		t.Error("expected output to contain 'assistant' badge in light theme")
	}
	if !strings.Contains(out, "light mode") {
		t.Error("expected output to contain content in light theme")
	}
}
