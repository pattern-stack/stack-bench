package molecules

import (
	"strings"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
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
type DiffBlockData struct {
	Filename string     // displayed as a Badge header
	Lines    []DiffLine // the diff content
}

// DiffBlock renders a colored unified diff.
// Header: Badge(filename, filled)
// Body: per-line colored output with gutter markers
func DiffBlock(ctx atoms.RenderContext, data DiffBlockData) string {
	var parts []string

	// Header: filename badge
	parts = append(parts, atoms.Badge(ctx, atoms.BadgeData{
		Label:   data.Filename,
		Style:   theme.Style{Hierarchy: theme.Secondary},
		Variant: atoms.BadgeFilled,
	}))

	if len(data.Lines) > 0 {
		// Blank line between header and body
		parts = append(parts, "")

		// Zero-width context for inline line rendering
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

// ParseUnifiedDiff converts a unified diff string into []DiffLine.
// Lines starting with '+' (not '+++') are Added, '-' (not '---') are Removed,
// @@ hunk headers are skipped, everything else is Context.
func ParseUnifiedDiff(diff string) []DiffLine {
	if diff == "" {
		return nil
	}

	var result []DiffLine
	for _, raw := range strings.Split(diff, "\n") {
		// Skip file headers and hunk headers
		if strings.HasPrefix(raw, "---") || strings.HasPrefix(raw, "+++") {
			continue
		}
		if strings.HasPrefix(raw, "@@") {
			continue
		}

		if strings.HasPrefix(raw, "+") {
			result = append(result, DiffLine{
				Type:    DiffAdded,
				Content: raw[1:],
			})
		} else if strings.HasPrefix(raw, "-") {
			result = append(result, DiffLine{
				Type:    DiffRemoved,
				Content: raw[1:],
			})
		} else {
			// Context line — strip leading space if present
			content := raw
			if strings.HasPrefix(content, " ") {
				content = content[1:]
			}
			result = append(result, DiffLine{
				Type:    DiffContext,
				Content: content,
			})
		}
	}

	return result
}
