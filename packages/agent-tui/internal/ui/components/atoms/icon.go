package atoms

import "github.com/dugshub/agent-tui/internal/ui/theme"

// IconName identifies a semantic glyph.
type IconName int

const (
	IconCursor  IconName = iota // >
	IconArrow                   // ->
	IconBullet                  // *
	IconCheck                   // checkmark
	IconX                       // x mark
	IconDot                     // filled circle
	IconCircle                  // empty circle
	IconWarning                 // triangle
	IconInfo                    // i
)

// glyphs maps icon names to their Unicode characters.
var glyphs = map[IconName]string{
	IconCursor:  ">",
	IconArrow:   "\u2192",
	IconBullet:  "\u2022",
	IconCheck:   "\u2713",
	IconX:       "\u2717",
	IconDot:     "\u25CF",
	IconCircle:  "\u25CB",
	IconWarning: "\u26A0",
	IconInfo:    "\u2139",
}

// Icon renders a semantic glyph with the given style.
func Icon(ctx RenderContext, name IconName, style theme.Style) string {
	glyph, ok := glyphs[name]
	if !ok {
		return ""
	}
	resolved := ctx.Theme.Resolve(style)
	return resolved.Render(glyph)
}
