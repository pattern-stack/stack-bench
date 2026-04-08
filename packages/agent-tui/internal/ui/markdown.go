package ui

import (
	"strings"
)

// MarkdownRenderer renders streaming markdown text progressively.
type MarkdownRenderer struct {
	buf   strings.Builder
	width int
}

func NewMarkdownRenderer(width int) *MarkdownRenderer {
	return &MarkdownRenderer{width: width}
}

func (r *MarkdownRenderer) WriteChunk(chunk string) { r.buf.WriteString(chunk) }
func (r *MarkdownRenderer) Reset()                  { r.buf.Reset() }
func (r *MarkdownRenderer) Text() string             { return r.buf.String() }
func (r *MarkdownRenderer) SetWidth(w int)           { r.width = w }
func (r *MarkdownRenderer) Render() string           { return RenderMarkdown(r.buf.String(), r.width) }

// RenderMarkdown converts a markdown string to styled terminal output.
// Uses goldmark for proper AST-based rendering with streaming fixup.
func RenderMarkdown(text string, width int) string {
	if text == "" {
		return ""
	}

	fixed := streamingFixup(text)
	return renderWithGoldmark(fixed, width)
}
