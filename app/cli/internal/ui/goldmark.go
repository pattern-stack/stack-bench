package ui

import (
	"bufio"
	"bytes"
	"fmt"
	"strings"
	"sync"

	"charm.land/lipgloss/v2"
	"github.com/yuin/goldmark"
	"github.com/yuin/goldmark/ast"
	gmext "github.com/yuin/goldmark/extension"
	east "github.com/yuin/goldmark/extension/ast"
	"github.com/yuin/goldmark/renderer"
	gmtext "github.com/yuin/goldmark/text"
	"github.com/yuin/goldmark/util"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// ---------------------------------------------------------------------------
// Streaming fixup -- close unclosed markdown constructs before parsing
// ---------------------------------------------------------------------------

// streamingFixup appends closing delimiters for any unclosed markdown
// constructs so that goldmark produces a well-formed AST even during
// streaming (when the text may be incomplete).
func streamingFixup(input string) string {
	var (
		inFence         bool
		fenceCount      int
		backtickRuns    int
		boldCount       int
		italicCount     int
		strikeCount     int
		openBracket     bool
		hasBracketParen bool
	)

	lines := strings.Split(input, "\n")
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "```") {
			fenceCount++
			inFence = !inFence
			continue
		}
		if inFence {
			continue
		}

		i := 0
		for i < len(line) {
			if line[i] == '`' {
				j := i + 1
				for j < len(line) && line[j] == '`' {
					j++
				}
				backtickRuns++
				i = j
				continue
			}
			if i+1 < len(line) && line[i] == '~' && line[i+1] == '~' {
				strikeCount++
				i += 2
				continue
			}
			if i+1 < len(line) && line[i] == '*' && line[i+1] == '*' {
				boldCount++
				i += 2
				continue
			}
			if line[i] == '*' {
				italicCount++
				i++
				continue
			}
			if line[i] == '[' {
				openBracket = true
				hasBracketParen = false
				i++
				continue
			}
			if line[i] == ']' && openBracket {
				if i+1 < len(line) && line[i+1] == '(' {
					hasBracketParen = true
					i += 2
					continue
				}
				openBracket = false
				i++
				continue
			}
			if line[i] == ')' && hasBracketParen {
				openBracket = false
				hasBracketParen = false
				i++
				continue
			}
			i++
		}
	}

	var suffix strings.Builder

	if fenceCount%2 != 0 {
		suffix.WriteString("\n```")
	}
	if fenceCount%2 == 0 && backtickRuns%2 != 0 {
		suffix.WriteString("`")
	}
	if boldCount%2 != 0 {
		suffix.WriteString("**")
	}
	if italicCount%2 != 0 {
		suffix.WriteString("*")
	}
	if strikeCount%2 != 0 {
		suffix.WriteString("~~")
	}
	if openBracket && hasBracketParen {
		suffix.WriteString(")")
	} else if openBracket && !hasBracketParen {
		suffix.WriteString("]()")
	}

	if suffix.Len() == 0 {
		return input
	}
	return input + suffix.String()
}

// ---------------------------------------------------------------------------
// Terminal renderer -- goldmark renderer.NodeRenderer implementation
// ---------------------------------------------------------------------------

type terminalRenderer struct {
	width      int
	ctx        atoms.RenderContext
	styleStack []lipgloss.Style
	inlineBuf  strings.Builder
}

func newTerminalRenderer(width int) *terminalRenderer {
	ctx := atoms.DefaultContext(width)
	return &terminalRenderer{
		width: width,
		ctx:   ctx,
	}
}

// RegisterFuncs implements renderer.NodeRenderer.
func (r *terminalRenderer) RegisterFuncs(reg renderer.NodeRendererFuncRegisterer) {
	// Block nodes
	reg.Register(ast.KindDocument, r.renderDocument)
	reg.Register(ast.KindHeading, r.renderHeading)
	reg.Register(ast.KindParagraph, r.renderParagraph)
	reg.Register(ast.KindFencedCodeBlock, r.renderFencedCodeBlock)
	reg.Register(ast.KindCodeBlock, r.renderIndentedCodeBlock)
	reg.Register(ast.KindBlockquote, r.renderBlockquote)
	reg.Register(ast.KindList, r.renderList)
	reg.Register(ast.KindListItem, r.renderListItem)
	reg.Register(ast.KindThematicBreak, r.renderThematicBreak)
	reg.Register(ast.KindHTMLBlock, r.renderHTMLBlock)

	// Inline nodes
	reg.Register(ast.KindText, r.renderText)
	reg.Register(ast.KindString, r.renderString)
	reg.Register(ast.KindEmphasis, r.renderEmphasis)
	reg.Register(ast.KindCodeSpan, r.renderCodeSpan)
	reg.Register(ast.KindLink, r.renderLink)
	reg.Register(ast.KindAutoLink, r.renderAutoLink)
	reg.Register(ast.KindImage, r.renderImage)
	reg.Register(ast.KindRawHTML, r.renderRawHTML)

	// GFM extensions
	reg.Register(east.KindStrikethrough, r.renderStrikethrough)
	reg.Register(east.KindTaskCheckBox, r.renderTaskCheckBox)
	reg.Register(east.KindTable, r.renderTable)
	reg.Register(east.KindTableHeader, r.renderTableHeader)
	reg.Register(east.KindTableRow, r.renderTableRow)
	reg.Register(east.KindTableCell, r.renderTableCell)
}

func (r *terminalRenderer) pushStyle(s lipgloss.Style) {
	r.styleStack = append(r.styleStack, s)
}

func (r *terminalRenderer) popStyle() {
	if len(r.styleStack) > 0 {
		r.styleStack = r.styleStack[:len(r.styleStack)-1]
	}
}

func (r *terminalRenderer) currentStyle() lipgloss.Style {
	if len(r.styleStack) > 0 {
		return r.styleStack[len(r.styleStack)-1]
	}
	return lipgloss.NewStyle()
}

// processMarkersWithBlock walks through text with markers, applying inline
// styles to marked portions and the blockStyle to unmarked portions.
func (r *terminalRenderer) processMarkersWithBlock(text string, blockStyle lipgloss.Style) string {
	return r.processMarkersImpl(text, &blockStyle)
}

// processMarkersImpl is the shared implementation.
// If blockStyle is non-nil, it is applied to text chunks outside any markers.
func (r *terminalRenderer) processMarkersImpl(text string, blockStyle *lipgloss.Style) string {
	if !strings.Contains(text, "\x00") {
		if blockStyle != nil {
			return blockStyle.Render(text)
		}
		return text
	}

	// First pass: collect styles in order of START markers
	var styles []lipgloss.Style
	{
		i := 0
		for i < len(text) {
			if text[i] == '\x00' {
				end := strings.IndexByte(text[i+1:], '\x00')
				if end < 0 {
					break
				}
				tag := text[i+1 : i+1+end]
				i = i + 1 + end + 1
				if strings.HasSuffix(tag, "_START") {
					styles = append(styles, r.getMarkerStyle(tag))
				}
				continue
			}
			i++
		}
	}

	// Second pass: render with styles
	var out strings.Builder
	var styleStack []lipgloss.Style
	styleIdx := 0
	i := 0

	for i < len(text) {
		if text[i] == '\x00' {
			end := strings.IndexByte(text[i+1:], '\x00')
			if end < 0 {
				out.WriteByte(text[i])
				i++
				continue
			}
			tag := text[i+1 : i+1+end]
			i = i + 1 + end + 1

			if strings.HasSuffix(tag, "_START") {
				if styleIdx < len(styles) {
					styleStack = append(styleStack, styles[styleIdx])
					styleIdx++
				}
			} else if strings.HasSuffix(tag, "_END") {
				if len(styleStack) > 0 {
					styleStack = styleStack[:len(styleStack)-1]
				}
			}
			continue
		}

		next := strings.IndexByte(text[i:], '\x00')
		var chunk string
		if next < 0 {
			chunk = text[i:]
			i = len(text)
		} else {
			chunk = text[i : i+next]
			i = i + next
		}

		if len(styleStack) > 0 {
			out.WriteString(styleStack[len(styleStack)-1].Render(chunk))
		} else if blockStyle != nil {
			out.WriteString(blockStyle.Render(chunk))
		} else {
			out.WriteString(chunk)
		}
	}

	return out.String()
}

// getMarkerStyle returns the lipgloss style for a given START marker tag.
func (r *terminalRenderer) getMarkerStyle(tag string) lipgloss.Style {
	switch tag {
	case "BOLD_START":
		return r.ctx.Theme.Resolve(theme.Style{Emphasis: theme.Strong})
	case "ITALIC_START":
		return lipgloss.NewStyle().Italic(true)
	case "LINK_START":
		s := r.ctx.Theme.Resolve(theme.Style{Category: theme.CatAgent, Hierarchy: theme.Secondary})
		return s.Underline(true)
	case "STRIKE_START":
		return lipgloss.NewStyle().Strikethrough(true)
	}
	return lipgloss.NewStyle()
}

// ---------------------------------------------------------------------------
// Block-level render functions
// ---------------------------------------------------------------------------

func (r *terminalRenderer) renderDocument(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderHeading(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	n := node.(*ast.Heading)
	if entering {
		var s theme.Style
		switch n.Level {
		case 1:
			s = theme.Style{Category: theme.CatAgent, Hierarchy: theme.Primary, Emphasis: theme.Strong}
		case 2:
			s = theme.Style{Category: theme.CatSystem, Hierarchy: theme.Primary, Emphasis: theme.Strong}
		case 3:
			s = theme.Style{Hierarchy: theme.Primary, Emphasis: theme.Strong}
		default:
			s = theme.Style{Hierarchy: theme.Secondary, Emphasis: theme.Strong}
		}
		resolved := r.ctx.Theme.Resolve(s)
		if r.width > 0 {
			resolved = resolved.Width(r.width)
		}
		r.pushStyle(resolved)
		r.inlineBuf.Reset()
	} else {
		style := r.currentStyle()
		r.popStyle()
		styled := r.flushInlineRaw(style)
		_, _ = w.WriteString(styled)
		_, _ = w.WriteString("\n")
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderParagraph(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if entering {
		s := theme.Style{Hierarchy: theme.Secondary}
		resolved := r.ctx.Theme.Resolve(s)
		if r.width > 0 {
			resolved = resolved.Width(r.width)
		}
		r.pushStyle(resolved)
		r.inlineBuf.Reset()
	} else {
		style := r.currentStyle()
		r.popStyle()
		styled := r.flushInlineRaw(style)
		_, _ = w.WriteString(styled)
		// Add blank line after paragraph for visual separation
		_, _ = w.WriteString("\n")
		if node.NextSibling() != nil {
			_, _ = w.WriteString("\n")
		}
	}
	return ast.WalkContinue, nil
}

// flushInlineRaw processes the inline buffer and renders through the block style.
func (r *terminalRenderer) flushInlineRaw(blockStyle lipgloss.Style) string {
	raw := r.inlineBuf.String()
	r.inlineBuf.Reset()

	if !strings.Contains(raw, "\x00") {
		return blockStyle.Render(raw)
	}

	// Separate width from color/weight styling. We apply color per-chunk
	// (so inline styles like bold/link override correctly) but width only
	// to the final assembled string (otherwise lipgloss pads each chunk).
	colorStyle := blockStyle.UnsetWidth()
	styled := r.processMarkersWithBlock(raw, colorStyle)

	// Re-apply width wrapping to the complete line if the original style had one.
	w := blockStyle.GetWidth()
	if w > 0 {
		styled = lipgloss.NewStyle().Width(w).Render(styled)
	}
	return styled
}

func (r *terminalRenderer) renderFencedCodeBlock(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if !entering {
		return ast.WalkContinue, nil
	}
	n := node.(*ast.FencedCodeBlock)
	lang := ""
	if n.Info != nil {
		lang = string(n.Info.Text(source))
		if idx := strings.IndexByte(lang, ' '); idx >= 0 {
			lang = lang[:idx]
		}
	}

	var code strings.Builder
	lines := n.Lines()
	for i := 0; i < lines.Len(); i++ {
		seg := lines.At(i)
		code.Write(seg.Value(source))
	}
	codeStr := strings.TrimRight(code.String(), "\n")

	rendered := atoms.CodeBlock(r.ctx, atoms.CodeBlockData{
		Code:     codeStr,
		Language: lang,
	})
	_, _ = w.WriteString(rendered)
	_, _ = w.WriteString("\n")
	return ast.WalkSkipChildren, nil
}

func (r *terminalRenderer) renderIndentedCodeBlock(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if !entering {
		return ast.WalkContinue, nil
	}
	n := node.(*ast.CodeBlock)

	var code strings.Builder
	lines := n.Lines()
	for i := 0; i < lines.Len(); i++ {
		seg := lines.At(i)
		code.Write(seg.Value(source))
	}
	codeStr := strings.TrimRight(code.String(), "\n")

	rendered := atoms.CodeBlock(r.ctx, atoms.CodeBlockData{
		Code: codeStr,
	})
	_, _ = w.WriteString(rendered)
	_, _ = w.WriteString("\n")
	return ast.WalkSkipChildren, nil
}

func (r *terminalRenderer) renderBlockquote(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if entering {
		childWidth := r.width - 4
		if childWidth < 10 {
			childWidth = 10
		}
		childBuf := renderNodeChildren(node, source, childWidth, r.ctx.Theme)
		gutterStyle := r.ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Tertiary})
		textStyle := r.ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Tertiary})
		gutter := gutterStyle.Render("\u2502 ")

		content := strings.TrimRight(childBuf, "\n")
		lines := strings.Split(content, "\n")
		for i, line := range lines {
			_, _ = w.WriteString(gutter + textStyle.Render(stripANSI(line)))
			if i < len(lines)-1 {
				_, _ = w.WriteString("\n")
			}
		}
		_, _ = w.WriteString("\n")
		return ast.WalkSkipChildren, nil
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderList(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderListItem(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if entering {
		n := node.(*ast.ListItem)
		list := n.Parent().(*ast.List)

		if list.IsOrdered() {
			num := list.Start
			for child := list.FirstChild(); child != nil; child = child.NextSibling() {
				if child == node {
					break
				}
				num++
			}
			numStyle := r.ctx.Theme.Resolve(theme.Style{Category: theme.CatAgent})
			_, _ = w.WriteString("  " + numStyle.Render(fmt.Sprintf("%d.", num)) + " ")
		} else {
			bullet := atoms.Icon(r.ctx, atoms.IconBullet, theme.Style{Category: theme.CatAgent})
			_, _ = w.WriteString("  " + bullet + " ")
		}

		s := theme.Style{Hierarchy: theme.Secondary}
		resolved := r.ctx.Theme.Resolve(s)
		itemWidth := r.width - 4
		if itemWidth > 0 {
			resolved = resolved.Width(itemWidth)
		}
		r.pushStyle(resolved)
		r.inlineBuf.Reset()
	} else {
		style := r.currentStyle()
		r.popStyle()
		styled := r.flushInlineRaw(style)
		_, _ = w.WriteString(styled)
		_, _ = w.WriteString("\n")
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderThematicBreak(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if !entering {
		return ast.WalkContinue, nil
	}
	_, _ = w.WriteString(atoms.Separator(r.ctx))
	_, _ = w.WriteString("\n")
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderHTMLBlock(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if !entering {
		return ast.WalkContinue, nil
	}
	n := node.(*ast.HTMLBlock)
	var content strings.Builder
	lines := n.Lines()
	for i := 0; i < lines.Len(); i++ {
		seg := lines.At(i)
		content.Write(seg.Value(source))
	}
	htmlText := stripHTMLTags(content.String())
	style := r.ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Tertiary})
	_, _ = w.WriteString(style.Render(htmlText))
	_, _ = w.WriteString("\n")
	return ast.WalkSkipChildren, nil
}

// ---------------------------------------------------------------------------
// Inline render functions
// ---------------------------------------------------------------------------

func (r *terminalRenderer) renderText(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if !entering {
		return ast.WalkContinue, nil
	}
	n := node.(*ast.Text)
	r.inlineBuf.Write(n.Text(source))
	if n.SoftLineBreak() {
		r.inlineBuf.WriteString(" ")
	}
	if n.HardLineBreak() {
		r.inlineBuf.WriteString("\n")
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderString(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if !entering {
		return ast.WalkContinue, nil
	}
	n := node.(*ast.String)
	r.inlineBuf.Write(n.Value)
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderEmphasis(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	n := node.(*ast.Emphasis)
	if entering {
		if n.Level == 2 {
			r.inlineBuf.WriteString("\x00BOLD_START\x00")
		} else {
			r.inlineBuf.WriteString("\x00ITALIC_START\x00")
		}
	} else {
		if n.Level == 2 {
			r.inlineBuf.WriteString("\x00BOLD_END\x00")
		} else {
			r.inlineBuf.WriteString("\x00ITALIC_END\x00")
		}
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderCodeSpan(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if entering {
		var code strings.Builder
		for child := node.FirstChild(); child != nil; child = child.NextSibling() {
			if t, ok := child.(*ast.Text); ok {
				code.Write(t.Text(source))
			}
		}
		inlineCtx := atoms.RenderContext{Width: 0, Theme: r.ctx.Theme}
		rendered := atoms.InlineCode(inlineCtx, code.String())
		r.inlineBuf.WriteString(rendered)
		return ast.WalkSkipChildren, nil
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderLink(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if entering {
		r.inlineBuf.WriteString("\x00LINK_START\x00")
	} else {
		r.inlineBuf.WriteString("\x00LINK_END\x00")
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderAutoLink(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if entering {
		n := node.(*ast.AutoLink)
		style := r.ctx.Theme.Resolve(theme.Style{Category: theme.CatAgent, Hierarchy: theme.Secondary})
		style = style.Underline(true)
		r.inlineBuf.WriteString(style.Render(string(n.Label(source))))
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderImage(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if entering {
		n := node.(*ast.Image)
		alt := string(n.Text(source))
		style := r.ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Tertiary})
		r.inlineBuf.WriteString(style.Render("[" + alt + "]"))
		return ast.WalkSkipChildren, nil
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderRawHTML(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if !entering {
		return ast.WalkContinue, nil
	}
	n := node.(*ast.RawHTML)
	segs := n.Segments
	var content strings.Builder
	for i := 0; i < segs.Len(); i++ {
		seg := segs.At(i)
		content.Write(seg.Value(source))
	}
	htmlText := stripHTMLTags(content.String())
	r.inlineBuf.WriteString(htmlText)
	return ast.WalkContinue, nil
}

// ---------------------------------------------------------------------------
// GFM extension render functions
// ---------------------------------------------------------------------------

func (r *terminalRenderer) renderStrikethrough(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if entering {
		r.inlineBuf.WriteString("\x00STRIKE_START\x00")
	} else {
		r.inlineBuf.WriteString("\x00STRIKE_END\x00")
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderTaskCheckBox(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if !entering {
		return ast.WalkContinue, nil
	}
	n := node.(*east.TaskCheckBox)
	if n.IsChecked {
		style := r.ctx.Theme.Resolve(theme.Style{Category: theme.CatAgent})
		r.inlineBuf.WriteString(style.Render("\u2611") + " ")
	} else {
		style := r.ctx.Theme.Resolve(theme.Style{Hierarchy: theme.Tertiary})
		r.inlineBuf.WriteString(style.Render("\u2610") + " ")
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderTable(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	if entering {
		table := node.(*east.Table)
		rendered := r.renderTableNode(table, source)
		_, _ = w.WriteString(rendered)
		_, _ = w.WriteString("\n")
		return ast.WalkSkipChildren, nil
	}
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderTableHeader(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderTableRow(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderTableCell(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error) {
	return ast.WalkContinue, nil
}

func (r *terminalRenderer) renderTableNode(tableNode *east.Table, source []byte) string {
	var headers []string
	var rows [][]string

	for child := tableNode.FirstChild(); child != nil; child = child.NextSibling() {
		var row []string
		isHeader := false
		if _, ok := child.(*east.TableHeader); ok {
			isHeader = true
		}
		for cell := child.FirstChild(); cell != nil; cell = cell.NextSibling() {
			var cellText strings.Builder
			for inline := cell.FirstChild(); inline != nil; inline = inline.NextSibling() {
				if t, ok := inline.(*ast.Text); ok {
					cellText.Write(t.Text(source))
				}
			}
			row = append(row, cellText.String())
		}
		if isHeader {
			headers = row
		} else {
			rows = append(rows, row)
		}
	}

	// Map goldmark alignments to atom alignments.
	var alignments []atoms.TableAlignment
	for _, a := range tableNode.Alignments {
		switch a {
		case east.AlignCenter:
			alignments = append(alignments, atoms.AlignCenter)
		case east.AlignRight:
			alignments = append(alignments, atoms.AlignRight)
		default:
			alignments = append(alignments, atoms.AlignLeft)
		}
	}

	return atoms.Table(r.ctx, atoms.TableData{
		Headers:    headers,
		Rows:       rows,
		Alignments: alignments,
	})
}

// ---------------------------------------------------------------------------
// Goldmark pipeline
// ---------------------------------------------------------------------------

var (
	gmOnce     sync.Once
	gmInstance goldmark.Markdown
)

func getGoldmark() goldmark.Markdown {
	gmOnce.Do(func() {
		gmInstance = goldmark.New(
			goldmark.WithExtensions(
				gmext.Table,
				gmext.Strikethrough,
				gmext.TaskList,
				gmext.Linkify,
			),
		)
	})
	return gmInstance
}

// renderWithGoldmark parses markdown and renders it through the terminal renderer.
func renderWithGoldmark(input string, width int) string {
	source := []byte(input)
	gm := getGoldmark()

	reader := gmtext.NewReader(source)
	doc := gm.Parser().Parse(reader)

	tr := newTerminalRenderer(width)
	var rawBuf bytes.Buffer
	bw := bufio.NewWriter(&rawBuf)

	handlers := make(map[ast.NodeKind]renderer.NodeRendererFunc)
	reg := &funcRegisterer{handlers: handlers}
	tr.RegisterFuncs(reg)

	_ = ast.Walk(doc, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
		handler, ok := handlers[n.Kind()]
		if !ok {
			return ast.WalkContinue, nil
		}
		status, err := handler(bw, source, n, entering)
		return status, err
	})
	_ = bw.Flush()

	result := rawBuf.String()
	result = strings.TrimRight(result, "\n")
	return result
}

// funcRegisterer collects handler registrations into a map.
type funcRegisterer struct {
	handlers map[ast.NodeKind]renderer.NodeRendererFunc
}

func (f *funcRegisterer) Register(kind ast.NodeKind, fn renderer.NodeRendererFunc) {
	f.handlers[kind] = fn
}

// renderNodeChildren renders the children of a node into a string using a fresh renderer.
func renderNodeChildren(node ast.Node, source []byte, width int, t *theme.Theme) string {
	tr := &terminalRenderer{
		width: width,
		ctx:   atoms.RenderContext{Width: width, Theme: t},
	}
	handlers := make(map[ast.NodeKind]renderer.NodeRendererFunc)
	reg := &funcRegisterer{handlers: handlers}
	tr.RegisterFuncs(reg)

	var rawBuf bytes.Buffer
	bw := bufio.NewWriter(&rawBuf)

	for child := node.FirstChild(); child != nil; child = child.NextSibling() {
		_ = ast.Walk(child, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
			handler, ok := handlers[n.Kind()]
			if !ok {
				return ast.WalkContinue, nil
			}
			status, err := handler(bw, source, n, entering)
			return status, err
		})
	}
	_ = bw.Flush()
	return rawBuf.String()
}

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

func stripHTMLTags(s string) string {
	var out strings.Builder
	inTag := false
	for _, r := range s {
		if r == '<' {
			inTag = true
			continue
		}
		if r == '>' {
			inTag = false
			continue
		}
		if !inTag {
			out.WriteRune(r)
		}
	}
	return out.String()
}

func stripANSI(s string) string {
	var out strings.Builder
	i := 0
	for i < len(s) {
		if s[i] == '\x1b' && i+1 < len(s) && s[i+1] == '[' {
			j := i + 2
			for j < len(s) && s[j] != 'm' {
				j++
			}
			if j < len(s) {
				i = j + 1
				continue
			}
		}
		out.WriteByte(s[i])
		i++
	}
	return out.String()
}
