package ui

import (
	"strings"

	"charm.land/lipgloss/v2"

	"github.com/dugshub/agent-tui/internal/ui/theme"
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

// mdStyles resolves markdown styles lazily against the active theme.
func mdStyles() (h1, h2, h3, bold, italic, code, codeBlock, link, listBullet lipgloss.Style) {
	t := theme.Active()
	h1 = lipgloss.NewStyle().Bold(true).Foreground(t.Categories[theme.CatAgent])
	h2 = lipgloss.NewStyle().Bold(true).Foreground(t.Foreground)
	h3 = lipgloss.NewStyle().Bold(true).Foreground(t.DimColor)
	bold = lipgloss.NewStyle().Bold(true)
	italic = lipgloss.NewStyle().Italic(true)
	code = lipgloss.NewStyle().Foreground(t.Statuses[theme.Success])
	codeBlock = lipgloss.NewStyle().Foreground(t.Statuses[theme.Success])
	link = lipgloss.NewStyle().Foreground(t.Categories[theme.CatAgent]).Underline(true)
	listBullet = lipgloss.NewStyle().Foreground(t.Categories[theme.CatAgent])
	return
}

// RenderMarkdown converts a markdown string to styled terminal output.
func RenderMarkdown(text string, width int) string {
	if text == "" {
		return ""
	}

	lines := strings.Split(text, "\n")
	var out []string
	inCodeBlock := false
	var codeBuf []string

	for _, line := range lines {
		if strings.HasPrefix(strings.TrimSpace(line), "```") {
			if inCodeBlock {
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

	if inCodeBlock && len(codeBuf) > 0 {
		out = append(out, renderCodeBlock(codeBuf, width))
	}

	return strings.Join(out, "\n")
}

func renderLine(line string, width int) string {
	_, _, mdH3, _, _, _, _, _, mdListBullet := mdStyles()
	mdH1, mdH2, _, _, _, _, _, _, _ := mdStyles()
	trimmed := strings.TrimSpace(line)

	if strings.HasPrefix(trimmed, "### ") {
		return mdH3.Render(trimmed[4:])
	}
	if strings.HasPrefix(trimmed, "## ") {
		return mdH2.Render(trimmed[3:])
	}
	if strings.HasPrefix(trimmed, "# ") {
		return mdH1.Render(trimmed[2:])
	}

	if strings.HasPrefix(trimmed, "- ") || strings.HasPrefix(trimmed, "* ") {
		bullet := mdListBullet.Render("•")
		content := renderInline(trimmed[2:])
		return "  " + bullet + " " + content
	}

	if idx := indexOfOrderedPrefix(trimmed); idx > 0 {
		num := trimmed[:idx]
		bullet := mdListBullet.Render(num)
		content := renderInline(trimmed[idx:])
		return "  " + bullet + content
	}

	return renderInline(line)
}

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

func renderInline(line string) string {
	_, _, _, mdBold, mdItalic, mdCode, _, mdLink, _ := mdStyles()
	var out strings.Builder
	i := 0

	for i < len(line) {
		if i+1 < len(line) && line[i] == '*' && line[i+1] == '*' {
			end := strings.Index(line[i+2:], "**")
			if end >= 0 {
				out.WriteString(mdBold.Render(line[i+2 : i+2+end]))
				i = i + 2 + end + 2
				continue
			}
		}

		if line[i] == '*' && (i+1 >= len(line) || line[i+1] != '*') {
			end := strings.IndexByte(line[i+1:], '*')
			if end >= 0 {
				out.WriteString(mdItalic.Render(line[i+1 : i+1+end]))
				i = i + 1 + end + 1
				continue
			}
		}

		if line[i] == '`' {
			end := strings.IndexByte(line[i+1:], '`')
			if end >= 0 {
				out.WriteString(mdCode.Render(line[i+1 : i+1+end]))
				i = i + 1 + end + 1
				continue
			}
		}

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
	_, _, _, _, _, _, mdCodeBlock, _, _ := mdStyles()
	content := strings.Join(lines, "\n")
	styled := mdCodeBlock.Render(content)

	var out []string
	for _, l := range strings.Split(styled, "\n") {
		out = append(out, theme.Dim().Render("│ ")+l)
	}
	return strings.Join(out, "\n")
}
