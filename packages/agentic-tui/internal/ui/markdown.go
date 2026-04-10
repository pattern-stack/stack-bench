package ui

import (
	"strings"
)

// MarkdownRenderer renders streaming markdown text progressively.
// Feed it incremental chunks via WriteChunk, then call Render to get
// styled output. Handles partial tokens gracefully (e.g. a chunk
// ending mid-codeblock fence).
type MarkdownRenderer struct {
	buf   strings.Builder
	width int
}

// NewMarkdownRenderer creates a renderer with the given display width.
func NewMarkdownRenderer(width int) *MarkdownRenderer {
	return &MarkdownRenderer{width: width}
}

// WriteChunk appends a text chunk to the buffer.
func (r *MarkdownRenderer) WriteChunk(chunk string) {
	r.buf.WriteString(chunk)
}

// Reset clears the accumulated text.
func (r *MarkdownRenderer) Reset() {
	r.buf.Reset()
}

// Text returns the raw accumulated text.
func (r *MarkdownRenderer) Text() string {
	return r.buf.String()
}

// SetWidth updates the display width.
func (r *MarkdownRenderer) SetWidth(w int) {
	r.width = w
}

// Render returns styled output from the accumulated markdown text.
func (r *MarkdownRenderer) Render() string {
	return RenderMarkdown(r.buf.String(), r.width)
}

// RenderMarkdown converts a markdown string to styled terminal output.
// It applies streaming fixup to handle unclosed constructs, then parses
// with goldmark and renders through the atom component system.
func RenderMarkdown(text string, width int) string {
	if text == "" {
		return ""
	}
	fixed := streamingFixup(text)
	return renderWithGoldmark(fixed, width)
}
