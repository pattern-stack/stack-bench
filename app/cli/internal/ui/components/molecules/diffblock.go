package molecules

import (
	"fmt"
	"image/color"
	"strconv"
	"strings"

	"charm.land/lipgloss/v2"
	"github.com/sergi/go-diff/diffmatchpatch"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// DiffBlockData holds parameters for rendering a unified diff display.
type DiffBlockData struct {
	FilePath string
	Diff     string // unified diff content (lines starting with +, -, or space)
	Language string // optional chroma language for syntax-highlighting line content
}

// Diff colors: muted red/blue (not green) for added/removed. Dark backgrounds
// so the change region reads as a tint, not a fill. Foreground colors for the
// marker glyph and flat-fallback content.
var (
	changeBgRemoved color.Color = lipgloss.Color("#2a1216") // very dark wine
	changeBgAdded   color.Color = lipgloss.Color("#121a2a") // very dark navy

	diffRemovedFg color.Color = lipgloss.Color("#d88080") // muted red for '-' marker
	diffAddedFg   color.Color = lipgloss.Color("#7a9eff") // muted blue for '+' marker
)

// diffEntry is one parsed line of the diff.
type diffEntry struct {
	kind    rune // '+', '-', ' ', or '@'
	content string
	oldNum  int
	newNum  int
}

// DiffBlock renders a file path header and color-coded diff lines. When
// Language is set, both added and removed lines are syntax-highlighted, and
// the changed substring within paired add/remove lines gets a faint background
// tint to mark exactly what changed.
func DiffBlock(ctx atoms.RenderContext, data DiffBlockData) string {
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}
	var parts []string

	// File path header
	if data.FilePath != "" {
		path := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  data.FilePath,
			Style: theme.Style{Category: theme.CatTool},
		})
		parts = append(parts, path)
	}

	entries := parseDiffEntries(data.Diff)
	regions := computeChangeRegions(entries)

	numStyle := theme.Style{Hierarchy: theme.Quaternary}

	// Prefix is "  NNNN M " — 2 indent + 4 number + 1 space + 1 marker + 1 space.
	const gutterWidth = 9
	maxContentWidth := 0
	if ctx.Width > gutterWidth {
		maxContentWidth = ctx.Width - gutterWidth
	}

	for idx, e := range entries {
		if e.kind == '@' {
			rendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text:  e.content,
				Style: theme.Style{Category: theme.CatSystem, Hierarchy: theme.Tertiary},
			})
			parts = append(parts, "  "+rendered)
			continue
		}

		// Compute line number and marker glyph + color.
		var num, marker string
		var markerFg color.Color
		var fallbackStyle theme.Style

		switch e.kind {
		case '+':
			num = fmt.Sprintf("%4d", e.newNum)
			marker = "+"
			markerFg = diffAddedFg
			fallbackStyle = theme.Style{Hierarchy: theme.Secondary}
		case '-':
			num = fmt.Sprintf("%4d", e.oldNum)
			marker = "-"
			markerFg = diffRemovedFg
			fallbackStyle = theme.Style{Hierarchy: theme.Secondary}
		default: // ' ' (context)
			num = fmt.Sprintf("%4d", e.newNum)
			marker = " "
			markerFg = nil
			fallbackStyle = theme.Style{Hierarchy: theme.Tertiary}
		}

		// Render content: chroma for +/- when language is set (with word-level
		// region highlights from diff-match-patch); flat fallback otherwise.
		var contentRendered string
		if data.Language != "" && (e.kind == '+' || e.kind == '-') {
			lineRanges := regions[idx]
			if len(lineRanges) > 0 {
				bg := changeBgRemoved
				if e.kind == '+' {
					bg = changeBgAdded
				}
				contentRendered = atoms.HighlightCodeRanges(
					inlineCtx, e.content, data.Language, lineRanges, bg,
				)
			} else {
				contentRendered = atoms.HighlightCode(inlineCtx, e.content, data.Language)
			}
		} else {
			contentRendered = atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text: e.content, Style: fallbackStyle,
			})
		}

		// Truncate content to fit within the available width so long lines
		// don't wrap and carry their background into the next terminal row.
		if maxContentWidth > 0 {
			contentRendered = lipgloss.NewStyle().MaxWidth(maxContentWidth).Render(contentRendered)
		}

		numRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text: num, Style: numStyle,
		})
		var markerRendered string
		if markerFg != nil {
			markerRendered = lipgloss.NewStyle().Foreground(markerFg).Render(marker)
		} else {
			markerRendered = marker
		}
		parts = append(parts, "  "+numRendered+" "+markerRendered+" "+contentRendered)
	}

	return strings.Join(parts, "\n")
}

// parseDiffEntries converts a unified diff into typed entries with line numbers.
func parseDiffEntries(diff string) []diffEntry {
	lines := strings.Split(diff, "\n")
	entries := make([]diffEntry, 0, len(lines))
	var oldLine, newLine int
	for _, line := range lines {
		switch {
		case strings.HasPrefix(line, "@@"):
			oldLine, newLine = parseHunkHeader(line)
			entries = append(entries, diffEntry{kind: '@', content: line})
		case strings.HasPrefix(line, "+"):
			entries = append(entries, diffEntry{
				kind: '+', content: strings.TrimPrefix(line, "+"),
				newNum: newLine,
			})
			newLine++
		case strings.HasPrefix(line, "-"):
			entries = append(entries, diffEntry{
				kind: '-', content: strings.TrimPrefix(line, "-"),
				oldNum: oldLine,
			})
			oldLine++
		default:
			entries = append(entries, diffEntry{
				kind: ' ', content: line,
				oldNum: oldLine, newNum: newLine,
			})
			oldLine++
			newLine++
		}
	}
	return entries
}

// computeChangeRegions uses diff-match-patch to compute exact byte ranges
// within each paired remove/add line that differ from their counterpart.
//
// For each maximal run of consecutive '-' lines followed by '+' lines, we
// join the removed content and added content into two strings (preserving
// newlines), run diff-match-patch, then walk the resulting edit operations
// and translate every Delete/Insert byte back to (line_index, local_offset)
// in the original entries. Newlines within Equal/Delete/Insert segments
// advance to the next line; they are never themselves marked as "changed".
//
// This approach mirrors how `git diff --color-words` works: the diff
// algorithm decides the alignment, not us. Rewrites and pure additions fall
// out naturally (entire lines are marked as Insert/Delete).
func computeChangeRegions(entries []diffEntry) map[int][]atoms.ByteRange {
	regions := make(map[int][]atoms.ByteRange)
	dmp := diffmatchpatch.New()

	i := 0
	for i < len(entries) {
		if entries[i].kind != '-' {
			i++
			continue
		}
		removedStart := i
		for i < len(entries) && entries[i].kind == '-' {
			i++
		}
		removedEnd := i
		addedStart := i
		for i < len(entries) && entries[i].kind == '+' {
			i++
		}
		addedEnd := i

		// A block needs both sides to have anything to diff against.
		if removedEnd == removedStart || addedEnd == addedStart {
			continue
		}

		oldStr := joinEntries(entries[removedStart:removedEnd])
		newStr := joinEntries(entries[addedStart:addedEnd])

		diffs := dmp.DiffMain(oldStr, newStr, false)
		diffs = dmp.DiffCleanupSemantic(diffs)

		// Walk the edit operations, tracking position in both the old and
		// new joined strings simultaneously. Translate each byte of
		// Delete/Insert back to (line_index, local_offset).
		oldLine, oldCol := removedStart, 0
		newLine, newCol := addedStart, 0

		for _, d := range diffs {
			switch d.Type {
			case diffmatchpatch.DiffEqual:
				oldLine, oldCol = advancePos(d.Text, oldLine, oldCol, nil)
				newLine, newCol = advancePos(d.Text, newLine, newCol, nil)
			case diffmatchpatch.DiffDelete:
				oldLine, oldCol = advancePos(d.Text, oldLine, oldCol, regions)
			case diffmatchpatch.DiffInsert:
				newLine, newCol = advancePos(d.Text, newLine, newCol, regions)
			}
		}
	}
	return regions
}

// joinEntries concatenates the content of the given entries separated by \n.
// The separator is critical: it's what diff-match-patch uses to decide line
// boundaries when it aligns the two strings.
func joinEntries(es []diffEntry) string {
	var sb strings.Builder
	for k, e := range es {
		if k > 0 {
			sb.WriteByte('\n')
		}
		sb.WriteString(e.content)
	}
	return sb.String()
}

// advancePos walks text byte-by-byte, advancing (line, col) across newlines.
// When recordInto is non-nil, each non-newline byte is appended to that
// line's change range list, merging with the previous range when contiguous.
func advancePos(text string, line, col int, recordInto map[int][]atoms.ByteRange) (int, int) {
	for j := 0; j < len(text); j++ {
		if text[j] == '\n' {
			line++
			col = 0
			continue
		}
		if recordInto != nil {
			existing := recordInto[line]
			if n := len(existing); n > 0 && existing[n-1].End == col {
				existing[n-1].End = col + 1
				recordInto[line] = existing
			} else {
				recordInto[line] = append(existing, atoms.ByteRange{Start: col, End: col + 1})
			}
		}
		col++
	}
	return line, col
}

// parseHunkHeader extracts old and new start line numbers from a @@ header.
func parseHunkHeader(line string) (oldStart, newStart int) {
	// Format: @@ -old,count +new,count @@
	parts := strings.SplitN(line, " ", 4)
	if len(parts) >= 3 {
		if old := strings.TrimPrefix(parts[1], "-"); old != "" {
			if n, _, ok := strings.Cut(old, ","); ok {
				oldStart, _ = strconv.Atoi(n)
			} else {
				oldStart, _ = strconv.Atoi(old)
			}
		}
		if nw := strings.TrimPrefix(parts[2], "+"); nw != "" {
			if n, _, ok := strings.Cut(nw, ","); ok {
				newStart, _ = strconv.Atoi(n)
			} else {
				newStart, _ = strconv.Atoi(nw)
			}
		}
	}
	return
}
