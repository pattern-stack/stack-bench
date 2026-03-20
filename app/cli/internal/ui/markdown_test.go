package ui

import (
	"strings"
	"testing"
)

func TestRenderMarkdown_Empty(t *testing.T) {
	result := RenderMarkdown("", 80)
	if result != "" {
		t.Errorf("expected empty string, got %q", result)
	}
}

func TestRenderMarkdown_H1(t *testing.T) {
	result := RenderMarkdown("# Hello World", 80)
	if !strings.Contains(result, "Hello World") {
		t.Errorf("H1 should contain 'Hello World', got %q", result)
	}
	// Should not contain the # prefix
	if strings.Contains(result, "#") {
		t.Errorf("H1 should strip '#' prefix, got %q", result)
	}
}

func TestRenderMarkdown_H2(t *testing.T) {
	result := RenderMarkdown("## Section", 80)
	if !strings.Contains(result, "Section") {
		t.Errorf("H2 should contain 'Section', got %q", result)
	}
	if strings.Contains(result, "##") {
		t.Errorf("H2 should strip '##' prefix, got %q", result)
	}
}

func TestRenderMarkdown_H3(t *testing.T) {
	result := RenderMarkdown("### Subsection", 80)
	if !strings.Contains(result, "Subsection") {
		t.Errorf("H3 should contain 'Subsection', got %q", result)
	}
	if strings.Contains(result, "###") {
		t.Errorf("H3 should strip '###' prefix, got %q", result)
	}
}

func TestRenderMarkdown_CodeBlock(t *testing.T) {
	input := "```\nfmt.Println(\"hello\")\n```"
	result := RenderMarkdown(input, 80)
	if !strings.Contains(result, "fmt.Println") {
		t.Errorf("code block should contain code content, got %q", result)
	}
}

func TestRenderMarkdown_UnclosedCodeBlock(t *testing.T) {
	// Simulates streaming — code block not yet closed
	input := "```\npartial code"
	result := RenderMarkdown(input, 80)
	if !strings.Contains(result, "partial code") {
		t.Errorf("unclosed code block should still render content, got %q", result)
	}
}

func TestRenderMarkdown_Bold(t *testing.T) {
	result := RenderMarkdown("this is **bold** text", 80)
	if !strings.Contains(result, "bold") {
		t.Errorf("should contain bold text, got %q", result)
	}
	// Should not contain the ** markers
	if strings.Contains(result, "**") {
		t.Errorf("should strip ** markers, got %q", result)
	}
}

func TestRenderMarkdown_Italic(t *testing.T) {
	result := RenderMarkdown("this is *italic* text", 80)
	if !strings.Contains(result, "italic") {
		t.Errorf("should contain italic text, got %q", result)
	}
}

func TestRenderMarkdown_InlineCode(t *testing.T) {
	result := RenderMarkdown("use `fmt.Println` here", 80)
	if !strings.Contains(result, "fmt.Println") {
		t.Errorf("should contain inline code, got %q", result)
	}
	// Backticks should be stripped
	if strings.Contains(result, "`") {
		t.Errorf("should strip backticks, got %q", result)
	}
}

func TestRenderMarkdown_UnorderedList(t *testing.T) {
	input := "- item one\n- item two\n* item three"
	result := RenderMarkdown(input, 80)
	// Bullets should be rendered
	if !strings.Contains(result, "item one") {
		t.Errorf("should contain list items, got %q", result)
	}
	// Should use bullet character
	if !strings.Contains(result, "\u2022") {
		t.Errorf("should contain bullet character, got %q", result)
	}
}

func TestRenderMarkdown_OrderedList(t *testing.T) {
	input := "1. first\n2. second"
	result := RenderMarkdown(input, 80)
	if !strings.Contains(result, "first") {
		t.Errorf("should contain list items, got %q", result)
	}
}

func TestRenderMarkdown_Link(t *testing.T) {
	result := RenderMarkdown("[click here](https://example.com)", 80)
	if !strings.Contains(result, "click here") {
		t.Errorf("should contain link text, got %q", result)
	}
	// URL should not be visible in rendered output
	if strings.Contains(result, "https://example.com") {
		t.Errorf("should not show raw URL, got %q", result)
	}
}

func TestRenderMarkdown_MultipleLines(t *testing.T) {
	input := "# Title\n\nSome text with **bold** and *italic*.\n\n- list item"
	result := RenderMarkdown(input, 80)
	if !strings.Contains(result, "Title") {
		t.Errorf("should contain title, got %q", result)
	}
	if !strings.Contains(result, "bold") {
		t.Errorf("should contain bold text, got %q", result)
	}
}

func TestMarkdownRenderer_StreamingChunks(t *testing.T) {
	r := NewMarkdownRenderer(80)
	r.WriteChunk("# He")
	r.WriteChunk("llo")

	text := r.Text()
	if text != "# Hello" {
		t.Errorf("accumulated text = %q, want %q", text, "# Hello")
	}

	rendered := r.Render()
	if !strings.Contains(rendered, "Hello") {
		t.Errorf("rendered should contain 'Hello', got %q", rendered)
	}

	r.Reset()
	if r.Text() != "" {
		t.Error("Reset should clear accumulated text")
	}
}
