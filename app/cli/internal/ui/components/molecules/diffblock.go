package molecules

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// DiffBlockData holds parameters for rendering a unified diff display.
type DiffBlockData struct {
	FilePath string
	Diff     string // unified diff content (lines starting with +, -, or space)
	Language string // optional chroma language for syntax-highlighting line content
}

// DiffBlock renders a file path header and color-coded diff lines.
// Added lines are green, removed lines are red, context lines are dim.
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

	// Parse diff lines with line number tracking
	// Format: "  NUM MARKER CONTENT" where MARKER is +/- or space
	lines := strings.Split(data.Diff, "\n")
	numStyle := theme.Style{Hierarchy: theme.Quaternary}

	var oldLine, newLine int
	for _, line := range lines {
		var contentStyle theme.Style
		var markerStyle theme.Style
		var num, marker, content string

		switch {
		case strings.HasPrefix(line, "@@"):
			// Hunk header — render as-is, no line number
			oldLine, newLine = parseHunkHeader(line)
			rendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text:  line,
				Style: theme.Style{Category: theme.CatSystem, Hierarchy: theme.Tertiary},
			})
			parts = append(parts, "  "+rendered)
			continue
		case strings.HasPrefix(line, "+"):
			num = fmt.Sprintf("%4d", newLine)
			marker = "+"
			content = strings.TrimPrefix(line, "+")
			markerStyle = theme.Style{Status: theme.Success}
			contentStyle = theme.Style{Status: theme.Success}
			newLine++
		case strings.HasPrefix(line, "-"):
			num = fmt.Sprintf("%4d", oldLine)
			marker = "-"
			content = strings.TrimPrefix(line, "-")
			markerStyle = theme.Style{Status: theme.Error}
			contentStyle = theme.Style{Status: theme.Error}
			oldLine++
		default:
			num = fmt.Sprintf("%4d", newLine)
			marker = " "
			content = line
			markerStyle = theme.Style{Hierarchy: theme.Tertiary}
			contentStyle = theme.Style{Hierarchy: theme.Tertiary}
			oldLine++
			newLine++
		}

		numRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text: num, Style: numStyle,
		})
		markerRendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text: marker, Style: markerStyle,
		})

		// Syntax-highlight ONLY added lines when language is set.
		// Removed lines stay solid red, context lines stay dim — they're not
		// the focus of the diff and the flat color helps the eye find adds.
		var contentRendered string
		if data.Language != "" && marker == "+" {
			contentRendered = atoms.HighlightCode(inlineCtx, content, data.Language)
		} else {
			contentRendered = atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text: content, Style: contentStyle,
			})
		}
		parts = append(parts, "  "+numRendered+" "+markerRendered+" "+contentRendered)
	}

	return strings.Join(parts, "\n")
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
