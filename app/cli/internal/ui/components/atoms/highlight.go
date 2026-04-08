package atoms

import (
	"image/color"
	"strings"

	"charm.land/lipgloss/v2"
	"github.com/alecthomas/chroma/v2"
	"github.com/alecthomas/chroma/v2/lexers"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// ByteRange is a half-open byte range [Start, End) within a string.
type ByteRange struct {
	Start, End int
}

// HighlightCode tokenizes code with chroma and renders each token with
// theme-mapped lipgloss styles. If the language is empty or unknown, the
// code is returned unstyled.
func HighlightCode(ctx RenderContext, code string, language string) string {
	return HighlightCodeRanges(ctx, code, language, nil, nil)
}

// HighlightCodeRanges renders code with chroma syntax highlighting and applies
// regionBg as a background color to tokens whose bytes overlap any of the
// given ranges. This enables word-level diff highlights — multiple changed
// substrings within a single line — without losing token foreground colors.
// When ranges is empty or regionBg is nil, no background is applied.
func HighlightCodeRanges(ctx RenderContext, code, language string, ranges []ByteRange, regionBg color.Color) string {
	if language == "" {
		return code
	}

	lexer := lexers.Get(language)
	if lexer == nil {
		return code
	}
	lexer = chroma.Coalesce(lexer)

	iter, err := lexer.Tokenise(nil, code)
	if err != nil {
		return code
	}

	hasRanges := len(ranges) > 0 && regionBg != nil

	var buf strings.Builder
	pos := 0
	for tok := iter(); tok != chroma.EOF; tok = iter() {
		tokStart := pos
		tokEnd := pos + len(tok.Value)
		pos = tokEnd

		style := tokenStyle(ctx.Theme, tok.Type)
		if hasRanges && overlapsAny(tokStart, tokEnd, ranges) {
			style = style.Background(regionBg)
		}
		buf.WriteString(style.Render(tok.Value))
	}
	return buf.String()
}

// overlapsAny reports whether [start, end) overlaps any range in ranges.
func overlapsAny(start, end int, ranges []ByteRange) bool {
	for _, r := range ranges {
		if end > r.Start && start < r.End {
			return true
		}
	}
	return false
}

// tokenStyle maps a chroma token type to a lipgloss style using our theme
// colors. We use chroma purely as a tokenizer and do all styling ourselves.
func tokenStyle(t *theme.Theme, tt chroma.TokenType) lipgloss.Style {
	switch {
	case tt.InCategory(chroma.Keyword):
		return lipgloss.NewStyle().Bold(true).Foreground(t.Categories[theme.CatAgent])
	case tt.InCategory(chroma.LiteralString):
		return lipgloss.NewStyle().Foreground(t.Statuses[theme.Success])
	case tt.InCategory(chroma.Comment):
		return lipgloss.NewStyle().Italic(true).Foreground(t.DimColor)
	case tt == chroma.NameFunction:
		return lipgloss.NewStyle().Foreground(t.Categories[theme.CatTool])
	case tt == chroma.NameBuiltin:
		return lipgloss.NewStyle().Foreground(t.Categories[theme.CatAgent])
	case tt.InCategory(chroma.LiteralNumber):
		return lipgloss.NewStyle().Foreground(t.Categories[theme.CatUser])
	case tt == chroma.Operator || tt.InCategory(chroma.Operator):
		return lipgloss.NewStyle().Foreground(t.Foreground)
	case tt == chroma.Punctuation || tt.InCategory(chroma.Punctuation):
		return lipgloss.NewStyle().Foreground(t.Foreground)
	default:
		return lipgloss.NewStyle().Foreground(t.Foreground)
	}
}
