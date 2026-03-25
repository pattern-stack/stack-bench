package molecules

import (
	"strings"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// MessageBlockData holds parameters for rendering a chat message.
type MessageBlockData struct {
	Role    atoms.Role
	Content string
}

// roleLabels maps roles to their display labels.
var roleLabels = map[atoms.Role]string{
	atoms.RoleUser:      "user",
	atoms.RoleAssistant: "assistant",
	atoms.RoleSystem:    "system",
}

// MessageBlock renders a chat message with a role badge and indented content.
func MessageBlock(ctx atoms.RenderContext, data MessageBlockData) string {
	badge := roleBadge(ctx, data.Role)

	// Reduce width for indentation
	contentCtx := ctx
	if contentCtx.Width > 4 {
		contentCtx.Width -= 4
	}
	content := atoms.TextBlock(contentCtx, atoms.TextBlockData{
		Text:  data.Content,
		Style: theme.Style{Hierarchy: theme.Secondary},
	})

	// Indent every line of content
	lines := strings.Split(content, "\n")
	for i, l := range lines {
		lines[i] = "  " + l
	}
	return badge + "\n" + strings.Join(lines, "\n")
}

// roleBadge returns the appropriately styled badge for a chat role.
func roleBadge(ctx atoms.RenderContext, role atoms.Role) string {
	label := roleLabels[role]
	if label == "" {
		label = "unknown"
	}

	switch role {
	case atoms.RoleUser:
		return atoms.Badge(ctx, atoms.BadgeData{
			Label:   label,
			Style:   theme.Style{Category: theme.CatUser},
			Variant: atoms.BadgeOutline,
		})
	case atoms.RoleAssistant:
		return atoms.Badge(ctx, atoms.BadgeData{
			Label:   label,
			Style:   theme.Style{Category: theme.CatAgent},
			Variant: atoms.BadgeFilled,
		})
	case atoms.RoleSystem:
		return atoms.Badge(ctx, atoms.BadgeData{
			Label:   label,
			Style:   theme.Style{Category: theme.CatSystem},
			Variant: atoms.BadgeOutline,
		})
	default:
		return atoms.Badge(ctx, atoms.BadgeData{
			Label:   label,
			Variant: atoms.BadgeOutline,
		})
	}
}
