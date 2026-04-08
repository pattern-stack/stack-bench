package molecules

import (
	"fmt"
	"strings"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// DiffBlockData holds parameters for rendering a unified diff display.
// Callers with a raw unified diff string should use ParseUnifiedDiff to
// construct the Hunks slice.
type DiffBlockData struct {
	FilePath string
	Hunks    []DiffHunk
	Language string // optional chroma language for syntax-highlighting content
}

// DiffBlock renders a file path header followed by one or more hunks of
// color-coded diff lines. Added lines are green, removed lines are red,
// context lines are dim. When Language is set, added lines are syntax-
// highlighted; removed lines stay in a solid red so the eye can find changes
// at a glance.
func DiffBlock(ctx atoms.RenderContext, data DiffBlockData) string {
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}
	var parts []string

	if data.FilePath != "" {
		path := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  data.FilePath,
			Style: theme.Style{Category: theme.CatTool},
		})
		parts = append(parts, path)
	}

	numStyle := theme.Style{Hierarchy: theme.Quaternary}

	for _, hunk := range data.Hunks {
		if hunk.RawHeader != "" {
			rendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text:  hunk.RawHeader,
				Style: theme.Style{Category: theme.CatSystem, Hierarchy: theme.Tertiary},
			})
			parts = append(parts, "  "+rendered)
		}
		for _, line := range hunk.Lines {
			parts = append(parts, renderDiffLine(inlineCtx, line, data.Language, numStyle))
		}
	}

	return strings.Join(parts, "\n")
}

// renderDiffLine renders a single parsed diff line as "  NUM MARKER CONTENT".
// The line number shares the marker's color so add/remove regions stand out
// in the gutter at a glance; context line numbers stay dim.
func renderDiffLine(ctx atoms.RenderContext, line DiffLine, language string, numStyle theme.Style) string {
	var num, marker string
	var markerStyle, contentStyle, lineNumStyle theme.Style

	switch line.Kind {
	case DiffLineAdded:
		num = fmt.Sprintf("%4d", line.NewNum)
		marker = "+"
		markerStyle = theme.Style{Status: theme.Success}
		contentStyle = theme.Style{Status: theme.Success}
		lineNumStyle = theme.Style{Status: theme.Success}
	case DiffLineRemoved:
		num = fmt.Sprintf("%4d", line.OldNum)
		marker = "-"
		markerStyle = theme.Style{Status: theme.Error}
		contentStyle = theme.Style{Status: theme.Error}
		lineNumStyle = theme.Style{Status: theme.Error}
	default: // DiffLineContext
		num = fmt.Sprintf("%4d", line.NewNum)
		marker = " "
		markerStyle = theme.Style{Hierarchy: theme.Tertiary}
		contentStyle = theme.Style{Hierarchy: theme.Tertiary}
		lineNumStyle = numStyle
	}

	numRendered := atoms.TextBlock(ctx, atoms.TextBlockData{
		Text: num, Style: lineNumStyle,
	})
	markerRendered := atoms.TextBlock(ctx, atoms.TextBlockData{
		Text: marker, Style: markerStyle,
	})

	// Syntax-highlight only added lines when a language is set. Removed lines
	// stay solid red and context lines stay dim — the flat color helps the eye
	// find adds in a busy diff.
	var contentRendered string
	if language != "" && line.Kind == DiffLineAdded {
		contentRendered = atoms.HighlightCode(ctx, line.Content, language)
	} else {
		contentRendered = atoms.TextBlock(ctx, atoms.TextBlockData{
			Text: line.Content, Style: contentStyle,
		})
	}

	return "  " + numRendered + " " + markerRendered + " " + contentRendered
}
