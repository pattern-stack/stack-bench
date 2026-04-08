package molecules

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/dugshub/agent-tui/internal/ui/components/atoms"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// DiffLineType identifies the kind of a diff line.
type DiffLineType int

const (
	DiffContext DiffLineType = iota
	DiffAdded
	DiffRemoved
)

// DiffLine represents a single line in a unified diff.
type DiffLine struct {
	Type    DiffLineType
	Content string
}

// DiffBlockData carries configuration for a DiffBlock.
// Provide either Lines (structured) or Diff (raw unified diff string).
type DiffBlockData struct {
	Filename string     // displayed as header
	FilePath string     // alias for Filename (used by gallery)
	Lines    []DiffLine // structured diff lines
	Diff     string     // raw unified diff content (used if Lines is nil)
}

// DiffBlock renders a file path header and color-coded diff lines.
// Added lines are green, removed lines are red, context lines are dim.
func DiffBlock(ctx atoms.RenderContext, data DiffBlockData) string {
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	// Resolve file path
	filePath := data.FilePath
	if filePath == "" {
		filePath = data.Filename
	}

	var parts []string

	// File path header
	if filePath != "" {
		path := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  filePath,
			Style: theme.Style{Category: theme.CatTool},
		})
		parts = append(parts, path)
	}

	// If raw diff string is provided, render with line numbers
	if data.Diff != "" {
		return renderRawDiff(ctx, parts, data.Diff)
	}

	// Structured DiffLine rendering
	if len(data.Lines) > 0 {
		parts = append(parts, "")
		lineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

		for _, line := range data.Lines {
			var prefix string
			var style theme.Style

			switch line.Type {
			case DiffAdded:
				prefix = "+"
				style = theme.Style{Status: theme.Success}
			case DiffRemoved:
				prefix = "-"
				style = theme.Style{Status: theme.Error}
			default:
				prefix = " "
				style = theme.Style{Hierarchy: theme.Tertiary}
			}

			rendered := atoms.TextBlock(lineCtx, atoms.TextBlockData{
				Text:  prefix + " " + line.Content,
				Style: style,
			})
			parts = append(parts, rendered)
		}
	}

	return strings.Join(parts, "\n")
}

// renderRawDiff handles raw unified diff strings with line number tracking.
func renderRawDiff(ctx atoms.RenderContext, parts []string, diff string) string {
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}
	lines := strings.Split(diff, "\n")
	numStyle := theme.Style{Hierarchy: theme.Quaternary}

	var oldLine, newLine int
	for _, line := range lines {
		switch {
		case strings.HasPrefix(line, "@@"):
			oldLine, newLine = parseHunkHeader(line)
			rendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text:  line,
				Style: theme.Style{Category: theme.CatSystem, Hierarchy: theme.Tertiary},
			})
			parts = append(parts, "  "+rendered)
		case strings.HasPrefix(line, "---") || strings.HasPrefix(line, "+++"):
			// Skip file headers
			continue
		case strings.HasPrefix(line, "+"):
			num := fmt.Sprintf("%4d", newLine)
			content := strings.TrimPrefix(line, "+")
			numRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{Text: num, Style: numStyle})
			markerRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{Text: "+", Style: theme.Style{Status: theme.Success}})
			contentRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{Text: content, Style: theme.Style{Status: theme.Success}})
			parts = append(parts, "  "+numRendered+" "+markerRendered+" "+contentRendered)
			newLine++
		case strings.HasPrefix(line, "-"):
			num := fmt.Sprintf("%4d", oldLine)
			content := strings.TrimPrefix(line, "-")
			numRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{Text: num, Style: numStyle})
			markerRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{Text: "-", Style: theme.Style{Status: theme.Error}})
			contentRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{Text: content, Style: theme.Style{Status: theme.Error}})
			parts = append(parts, "  "+numRendered+" "+markerRendered+" "+contentRendered)
			oldLine++
		default:
			num := fmt.Sprintf("%4d", newLine)
			numRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{Text: num, Style: numStyle})
			markerRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{Text: " ", Style: theme.Style{Hierarchy: theme.Tertiary}})
			contentRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{Text: line, Style: theme.Style{Hierarchy: theme.Tertiary}})
			parts = append(parts, "  "+numRendered+" "+markerRendered+" "+contentRendered)
			oldLine++
			newLine++
		}
	}

	return strings.Join(parts, "\n")
}

// parseHunkHeader extracts old and new start line numbers from a @@ header.
func parseHunkHeader(line string) (oldStart, newStart int) {
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

// ParseUnifiedDiff converts a unified diff string into []DiffLine.
// Lines starting with '+' (not '+++') are Added, '-' (not '---') are Removed,
// @@ hunk headers are skipped, everything else is Context.
func ParseUnifiedDiff(diff string) []DiffLine {
	if diff == "" {
		return nil
	}

	var result []DiffLine
	for _, raw := range strings.Split(diff, "\n") {
		if strings.HasPrefix(raw, "---") || strings.HasPrefix(raw, "+++") {
			continue
		}
		if strings.HasPrefix(raw, "@@") {
			continue
		}

		if strings.HasPrefix(raw, "+") {
			result = append(result, DiffLine{Type: DiffAdded, Content: raw[1:]})
		} else if strings.HasPrefix(raw, "-") {
			result = append(result, DiffLine{Type: DiffRemoved, Content: raw[1:]})
		} else {
			content := raw
			if strings.HasPrefix(content, " ") {
				content = content[1:]
			}
			result = append(result, DiffLine{Type: DiffContext, Content: content})
		}
	}

	return result
}
