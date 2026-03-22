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
	// Strip ANSI escapes before checking content -- lipgloss v2 may wrap
	// individual graphemes in separate escape sequences for combined styles.
	plain := stripANSI(result)
	if !strings.Contains(plain, "click here") {
		t.Errorf("should contain link text, got plain=%q raw=%q", plain, result)
	}
	// URL should not be visible in rendered output
	if strings.Contains(plain, "https://example.com") {
		t.Errorf("should not show raw URL, got %q", plain)
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

// ---------------------------------------------------------------------------
// Blockquote rendering
// ---------------------------------------------------------------------------

func TestRenderMarkdown_Blockquote(t *testing.T) {
	result := RenderMarkdown("> This is a quote", 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "\u2502") {
		t.Errorf("blockquote should contain gutter character, got plain=%q", plain)
	}
	if !strings.Contains(plain, "This is a quote") {
		t.Errorf("blockquote should contain content text, got plain=%q", plain)
	}
}

func TestRenderMarkdown_BlockquoteMultiline(t *testing.T) {
	input := "> line one\n> line two"
	result := RenderMarkdown(input, 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "line one") {
		t.Errorf("blockquote should contain first line, got plain=%q", plain)
	}
	if !strings.Contains(plain, "line two") {
		t.Errorf("blockquote should contain second line, got plain=%q", plain)
	}
}

// ---------------------------------------------------------------------------
// Strikethrough rendering (GFM)
// ---------------------------------------------------------------------------

func TestRenderMarkdown_Strikethrough(t *testing.T) {
	result := RenderMarkdown("this is ~~deleted~~ text", 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "deleted") {
		t.Errorf("strikethrough should contain text, got plain=%q", plain)
	}
	if strings.Contains(plain, "~~") {
		t.Errorf("strikethrough should strip ~~ markers, got plain=%q", plain)
	}
}

// ---------------------------------------------------------------------------
// Task list rendering (GFM)
// ---------------------------------------------------------------------------

func TestRenderMarkdown_TaskListChecked(t *testing.T) {
	result := RenderMarkdown("- [x] done task", 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "\u2611") {
		t.Errorf("checked task should contain checked box glyph, got plain=%q", plain)
	}
	if !strings.Contains(plain, "done task") {
		t.Errorf("checked task should contain text, got plain=%q", plain)
	}
}

func TestRenderMarkdown_TaskListUnchecked(t *testing.T) {
	result := RenderMarkdown("- [ ] todo task", 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "\u2610") {
		t.Errorf("unchecked task should contain unchecked box glyph, got plain=%q", plain)
	}
	if !strings.Contains(plain, "todo task") {
		t.Errorf("unchecked task should contain text, got plain=%q", plain)
	}
}

// ---------------------------------------------------------------------------
// Nested inline formatting
// ---------------------------------------------------------------------------

func TestRenderMarkdown_BoldInsideList(t *testing.T) {
	result := RenderMarkdown("- **bold item**", 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "bold item") {
		t.Errorf("bold inside list should contain text, got plain=%q", plain)
	}
	if strings.Contains(plain, "**") {
		t.Errorf("should strip ** markers, got plain=%q", plain)
	}
}

func TestRenderMarkdown_CodeInsideBold(t *testing.T) {
	result := RenderMarkdown("**bold `code` text**", 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "code") {
		t.Errorf("code inside bold should contain code text, got plain=%q", plain)
	}
	if !strings.Contains(plain, "bold") {
		t.Errorf("should contain bold text, got plain=%q", plain)
	}
}

func TestRenderMarkdown_MixedInline(t *testing.T) {
	result := RenderMarkdown("**bold *and italic* together**", 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "bold") {
		t.Errorf("should contain bold text, got plain=%q", plain)
	}
	if !strings.Contains(plain, "and italic") {
		t.Errorf("should contain italic text, got plain=%q", plain)
	}
	if strings.Contains(plain, "**") || strings.Contains(plain, "*and") {
		t.Errorf("should strip markdown markers, got plain=%q", plain)
	}
}

// ---------------------------------------------------------------------------
// Streaming fixup
// ---------------------------------------------------------------------------

func TestStreamingFixup_UnclosedFence(t *testing.T) {
	input := "```\nsome code"
	result := streamingFixup(input)
	if !strings.HasSuffix(result, "```") {
		t.Errorf("should close unclosed fence, got %q", result)
	}
}

func TestStreamingFixup_UnclosedBold(t *testing.T) {
	input := "this is **bold"
	result := streamingFixup(input)
	if !strings.HasSuffix(result, "**") {
		t.Errorf("should close unclosed bold, got %q", result)
	}
}

func TestStreamingFixup_UnclosedItalic(t *testing.T) {
	input := "this is *italic"
	result := streamingFixup(input)
	if !strings.HasSuffix(result, "*") {
		t.Errorf("should close unclosed italic, got %q", result)
	}
}

func TestStreamingFixup_UnclosedInlineCode(t *testing.T) {
	input := "use `code"
	result := streamingFixup(input)
	if !strings.HasSuffix(result, "`") {
		t.Errorf("should close unclosed inline code, got %q", result)
	}
}

func TestStreamingFixup_UnclosedStrikethrough(t *testing.T) {
	input := "this is ~~struck"
	result := streamingFixup(input)
	if !strings.HasSuffix(result, "~~") {
		t.Errorf("should close unclosed strikethrough, got %q", result)
	}
}

func TestStreamingFixup_UnclosedLink(t *testing.T) {
	input := "[text](http://example.com"
	result := streamingFixup(input)
	if !strings.HasSuffix(result, ")") {
		t.Errorf("should close unclosed link URL, got %q", result)
	}
}

func TestStreamingFixup_ValidInputUnchanged(t *testing.T) {
	input := "just **normal** text with `code` and *italic*"
	result := streamingFixup(input)
	if result != input {
		t.Errorf("valid input should pass through unchanged, got %q", result)
	}
}

func TestStreamingFixup_DelimitersInsideFenceIgnored(t *testing.T) {
	input := "```\n**bold** inside fence\n```"
	result := streamingFixup(input)
	if result != input {
		t.Errorf("delimiters inside fence should be ignored, got %q", result)
	}
}

// ---------------------------------------------------------------------------
// Table rendering (GFM)
// ---------------------------------------------------------------------------

func TestRenderMarkdown_Table(t *testing.T) {
	input := "| Name | Age |\n|------|-----|\n| Alice | 30 |\n| Bob | 25 |"
	result := RenderMarkdown(input, 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "Name") {
		t.Errorf("table should contain header text, got plain=%q", plain)
	}
	if !strings.Contains(plain, "Alice") {
		t.Errorf("table should contain cell text, got plain=%q", plain)
	}
	if !strings.Contains(plain, "Bob") {
		t.Errorf("table should contain cell text, got plain=%q", plain)
	}
}

// ---------------------------------------------------------------------------
// Heading levels
// ---------------------------------------------------------------------------

func TestRenderMarkdown_H4(t *testing.T) {
	result := RenderMarkdown("#### Deep heading", 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "Deep heading") {
		t.Errorf("H4 should contain text, got plain=%q", plain)
	}
	if strings.Contains(plain, "####") {
		t.Errorf("H4 should strip '####' prefix, got plain=%q", plain)
	}
}

// ---------------------------------------------------------------------------
// Thematic break
// ---------------------------------------------------------------------------

func TestRenderMarkdown_ThematicBreak(t *testing.T) {
	result := RenderMarkdown("above\n\n---\n\nbelow", 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "\u2500") {
		t.Errorf("thematic break should produce separator character, got plain=%q", plain)
	}
}

// ---------------------------------------------------------------------------
// Fenced code block with language
// ---------------------------------------------------------------------------

func TestRenderMarkdown_FencedCodeWithLanguage(t *testing.T) {
	input := "```go\nfmt.Println(\"hello\")\n```"
	result := RenderMarkdown(input, 80)
	plain := stripANSI(result)
	if !strings.Contains(plain, "go") {
		t.Errorf("fenced code block should show language label, got plain=%q", plain)
	}
	if !strings.Contains(plain, "fmt.Println") {
		t.Errorf("fenced code block should contain code, got plain=%q", plain)
	}
}

// ---------------------------------------------------------------------------
// Edge cases
// ---------------------------------------------------------------------------

func TestRenderMarkdown_SingleNewline(t *testing.T) {
	// Should not crash
	result := RenderMarkdown("\n", 80)
	_ = result
}

func TestStreamingFixup_PartialFence(t *testing.T) {
	// Two backticks, not three -- should not be treated as a fence
	input := "some ``partial"
	result := streamingFixup(input)
	// The backtick run count is 2 (even), so no backtick fixup needed
	// but since we have `` which is 1 run (even count of runs = 2 runs for opening+closing? no)
	// Actually the code counts backtick *runs* not individual backticks.
	// Two separate `` groups = 1 run, which is odd, so it appends a closing backtick
	if !strings.HasSuffix(result, "`") {
		t.Errorf("odd backtick run should be closed, got %q", result)
	}
}
