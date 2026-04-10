package atoms

import (
	"strings"

	"charm.land/lipgloss/v2"
	"github.com/alecthomas/chroma/v2"
	"github.com/alecthomas/chroma/v2/lexers"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

// HighlightCode tokenizes code with chroma and renders each token with
// theme-mapped lipgloss styles. If the language is empty or unknown, the
// code is returned unstyled.
func HighlightCode(ctx RenderContext, code string, language string) string {
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

	var buf strings.Builder
	for tok := iter(); tok != chroma.EOF; tok = iter() {
		style := tokenStyle(ctx.Theme, tok.Type)
		buf.WriteString(style.Render(tok.Value))
	}
	return buf.String()
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
