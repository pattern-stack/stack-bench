package ui

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
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

// Markdown styles.
var (
	mdH1         = lipgloss.NewStyle().Bold(true).Foreground(ColorAccent)
	mdH2         = lipgloss.NewStyle().Bold(true).Foreground(ColorFg)
	mdH3         = lipgloss.NewStyle().Bold(true).Foreground(ColorDim)
	mdBold       = lipgloss.NewStyle().Bold(true)
	mdItalic     = lipgloss.NewStyle().Italic(true)
	mdCode       = lipgloss.NewStyle().Foreground(ColorGreen)
	mdCodeBlock  = lipgloss.NewStyle().Foreground(ColorGreen)
	mdLink       = lipgloss.NewStyle().Foreground(ColorAccent).Underline(true)
	mdListBullet = lipgloss.NewStyle().Foreground(ColorAccent)
)

// RenderMarkdown converts a markdown string to styled terminal output.
// It handles: headers, bold, italic, code blocks, inline code, lists, links.
func RenderMarkdown(text string, width int) string {
	if text == "" {
		return ""
	}

	lines := strings.Split(text, "\n")
	var out []string
	inCodeBlock := false
	var codeBuf []string

	for _, line := range lines {
		// Code block fences
		if strings.HasPrefix(strings.TrimSpace(line), "```") {
			if inCodeBlock {
				// Close code block
				out = append(out, renderCodeBlock(codeBuf, width))
				codeBuf = nil
				inCodeBlock = false
			} else {
				inCodeBlock = true
			}
			continue
		}

		if inCodeBlock {
			codeBuf = append(codeBuf, line)
			continue
		}

		out = append(out, renderLine(line, width))
	}

	// If we're in an unclosed code block (streaming), render what we have
	if inCodeBlock && len(codeBuf) > 0 {
		out = append(out, renderCodeBlock(codeBuf, width))
	}

	return strings.Join(out, "\n")
}

func renderLine(line string, width int) string {
	trimmed := strings.TrimSpace(line)

	// Headers
	if strings.HasPrefix(trimmed, "### ") {
		return mdH3.Render(trimmed[4:])
	}
	if strings.HasPrefix(trimmed, "## ") {
		return mdH2.Render(trimmed[3:])
	}
	if strings.HasPrefix(trimmed, "# ") {
		return mdH1.Render(trimmed[2:])
	}

	// Unordered list items
	if strings.HasPrefix(trimmed, "- ") || strings.HasPrefix(trimmed, "* ") {
		bullet := mdListBullet.Render("•")
		content := renderInline(trimmed[2:])
		return "  " + bullet + " " + content
	}

	// Ordered list items
	if idx := indexOfOrderedPrefix(trimmed); idx > 0 {
		num := trimmed[:idx]
		bullet := mdListBullet.Render(num)
		content := renderInline(trimmed[idx:])
		return "  " + bullet + content
	}

	// Regular line with inline formatting
	return renderInline(line)
}

// indexOfOrderedPrefix returns the length of an ordered list prefix like "1. "
// or 0 if no prefix is found.
func indexOfOrderedPrefix(s string) int {
	for i := 0; i < len(s) && i < 4; i++ {
		if s[i] >= '0' && s[i] <= '9' {
			continue
		}
		if s[i] == '.' && i > 0 && i+1 < len(s) && s[i+1] == ' ' {
			return i + 2
		}
		break
	}
	return 0
}

// renderInline handles bold, italic, inline code, and links within a line.
func renderInline(line string) string {
	var out strings.Builder
	i := 0

	for i < len(line) {
		// Bold: **text**
		if i+1 < len(line) && line[i] == '*' && line[i+1] == '*' {
			end := strings.Index(line[i+2:], "**")
			if end >= 0 {
				out.WriteString(mdBold.Render(line[i+2 : i+2+end]))
				i = i + 2 + end + 2
				continue
			}
		}

		// Italic: *text* (single asterisk, not followed by another)
		if line[i] == '*' && (i+1 >= len(line) || line[i+1] != '*') {
			end := strings.IndexByte(line[i+1:], '*')
			if end >= 0 {
				out.WriteString(mdItalic.Render(line[i+1 : i+1+end]))
				i = i + 1 + end + 1
				continue
			}
		}

		// Inline code: `text`
		if line[i] == '`' {
			end := strings.IndexByte(line[i+1:], '`')
			if end >= 0 {
				out.WriteString(mdCode.Render(line[i+1 : i+1+end]))
				i = i + 1 + end + 1
				continue
			}
		}

		// Links: [text](url)
		if line[i] == '[' {
			closeBracket := strings.IndexByte(line[i+1:], ']')
			if closeBracket >= 0 {
				afterBracket := i + 1 + closeBracket + 1
				if afterBracket < len(line) && line[afterBracket] == '(' {
					closeParen := strings.IndexByte(line[afterBracket+1:], ')')
					if closeParen >= 0 {
						linkText := line[i+1 : i+1+closeBracket]
						out.WriteString(mdLink.Render(linkText))
						i = afterBracket + 1 + closeParen + 1
						continue
					}
				}
			}
		}

		out.WriteByte(line[i])
		i++
	}

	return out.String()
}

func renderCodeBlock(lines []string, width int) string {
	content := strings.Join(lines, "\n")
	styled := mdCodeBlock.Render(content)

	// Add left border for visual distinction
	var out []string
	for _, l := range strings.Split(styled, "\n") {
		out = append(out, Dim.Render("│ ")+l)
	}
	return strings.Join(out, "\n")
}
