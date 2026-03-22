package app

import (
	"strings"

	"github.com/dugshub/stack-bench/app/cli/internal/api"
	"github.com/dugshub/stack-bench/app/cli/internal/chat"
	"github.com/dugshub/stack-bench/app/cli/internal/command"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/molecules"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// NewGallery creates a Model pre-loaded with a component gallery.
// All messages are pre-rendered so the user can scroll through immediately.
func NewGallery() Model {
	client := &api.StubClient{}
	m := Model{
		width:    80,
		height:   24,
		phase:    PhaseChat,
		client:   client,
		registry: command.DefaultRegistry(),
		gallery:  true,
	}
	m.chat = chat.New(client, "Component Gallery", m.registry)
	m.chat.SetSize(m.width, m.height-5)
	m.chat.SetConversationID("gallery")
	return m
}

// buildGalleryMessages creates the full gallery as raw chat messages.
func buildGalleryMessages(width int) []chat.Message {
	ctx := atoms.DefaultContext(width)
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}
	var msgs []chat.Message

	raw := func(content string) {
		msgs = append(msgs, chat.Message{Raw: true, Content: content + "\n"})
	}

	section := func(title, description string) string {
		header := molecules.Header(ctx, molecules.HeaderData{
			Title: title,
		})
		desc := atoms.TextBlock(ctx, atoms.TextBlockData{
			Text:  description,
			Style: theme.Style{Hierarchy: theme.Tertiary},
		})
		return header + "\n" + desc
	}

	// ── Atoms ──────────────────────────────────────────────────

	// TextBlock
	{
		var parts []string
		parts = append(parts, section("TextBlock", "Styled text with theme token resolution and word wrapping."))
		parts = append(parts, "")
		parts = append(parts, atoms.TextBlock(ctx, atoms.TextBlockData{
			Text:  "Primary text — the default hierarchy. Bold and prominent.",
			Style: theme.Style{Hierarchy: theme.Primary},
		}))
		parts = append(parts, atoms.TextBlock(ctx, atoms.TextBlockData{
			Text:  "Secondary text — body copy, readable but not dominant.",
			Style: theme.Style{Hierarchy: theme.Secondary},
		}))
		parts = append(parts, atoms.TextBlock(ctx, atoms.TextBlockData{
			Text:  "Tertiary text — dim, used for hints and metadata.",
			Style: theme.Style{Hierarchy: theme.Tertiary},
		}))
		parts = append(parts, atoms.TextBlock(ctx, atoms.TextBlockData{
			Text:  "Quaternary text — dim italic, used for line numbers and timestamps.",
			Style: theme.Style{Hierarchy: theme.Quaternary},
		}))
		parts = append(parts, "")
		parts = append(parts, atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  "Strong emphasis",
			Style: theme.Style{Emphasis: theme.Strong},
		}))
		parts = append(parts, atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  "Subtle emphasis",
			Style: theme.Style{Emphasis: theme.Subtle},
		}))
		raw(strings.Join(parts, "\n"))
	}

	// Badge
	{
		var parts []string
		parts = append(parts, section("Badge", "Inline labels for roles, status, and categories. Filled or outline variant."))
		parts = append(parts, "")

		// Filled badges
		filled := []struct {
			label string
			style theme.Style
		}{
			{"assistant", theme.Style{Category: theme.CatAgent}},
			{"success", theme.Style{Status: theme.Success}},
			{"error", theme.Style{Status: theme.Error}},
			{"warning", theme.Style{Status: theme.Warning}},
			{"info", theme.Style{Status: theme.Info}},
			{"running", theme.Style{Status: theme.Running}},
		}
		var filledRow []string
		for _, b := range filled {
			filledRow = append(filledRow, atoms.Badge(inlineCtx, atoms.BadgeData{
				Label: b.label, Style: b.style, Variant: atoms.BadgeFilled,
			}))
		}
		parts = append(parts, "  Filled:  "+strings.Join(filledRow, "  "))

		// Outline badges
		outline := []struct {
			label string
			style theme.Style
		}{
			{"user", theme.Style{Category: theme.CatUser}},
			{"system", theme.Style{Category: theme.CatSystem}},
			{"tool", theme.Style{Category: theme.CatTool}},
			{"agent", theme.Style{Category: theme.CatAgent}},
			{"muted", theme.Style{Status: theme.Muted}},
		}
		var outlineRow []string
		for _, b := range outline {
			outlineRow = append(outlineRow, atoms.Badge(inlineCtx, atoms.BadgeData{
				Label: b.label, Style: b.style, Variant: atoms.BadgeOutline,
			}))
		}
		parts = append(parts, "  Outline: "+strings.Join(outlineRow, "  "))

		raw(strings.Join(parts, "\n"))
	}

	// Icon
	{
		var parts []string
		parts = append(parts, section("Icon", "Semantic glyphs for status, navigation, and indicators."))
		parts = append(parts, "")

		icons := []struct {
			name  atoms.IconName
			label string
			style theme.Style
		}{
			{atoms.IconCursor, "cursor", theme.Style{Category: theme.CatAgent}},
			{atoms.IconArrow, "arrow", theme.Style{}},
			{atoms.IconBullet, "bullet", theme.Style{}},
			{atoms.IconCheck, "check", theme.Style{Status: theme.Success}},
			{atoms.IconX, "x", theme.Style{Status: theme.Error}},
			{atoms.IconDot, "dot", theme.Style{Status: theme.Warning}},
			{atoms.IconCircle, "circle", theme.Style{Hierarchy: theme.Tertiary}},
			{atoms.IconWarning, "warning", theme.Style{Status: theme.Warning}},
			{atoms.IconInfo, "info", theme.Style{Status: theme.Info}},
		}
		var iconRow []string
		for _, ic := range icons {
			glyph := atoms.Icon(inlineCtx, ic.name, ic.style)
			label := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text: ic.label, Style: theme.Style{Hierarchy: theme.Tertiary},
			})
			iconRow = append(iconRow, glyph+" "+label)
		}
		parts = append(parts, "  "+strings.Join(iconRow, "   "))

		raw(strings.Join(parts, "\n"))
	}

	// Separator
	{
		var parts []string
		parts = append(parts, section("Separator", "Full-width horizontal rule."))
		parts = append(parts, "")
		parts = append(parts, atoms.Separator(ctx))
		raw(strings.Join(parts, "\n"))
	}

	// InlineCode
	{
		var parts []string
		parts = append(parts, section("InlineCode", "Monospace span for inline code references."))
		parts = append(parts, "")
		text := "  Use " + atoms.InlineCode(inlineCtx, "theme.Resolve()") + " to resolve tokens, not " + atoms.InlineCode(inlineCtx, "lipgloss.NewStyle()") + " directly."
		parts = append(parts, text)
		raw(strings.Join(parts, "\n"))
	}

	// CodeBlock
	{
		var parts []string
		parts = append(parts, section("CodeBlock", "Syntax-highlighted code with gutter and optional line numbers."))

		parts = append(parts, atoms.CodeBlock(ctx, atoms.CodeBlockData{
			Language:    "go",
			FilePath:    "internal/ui/components/atoms/textblock.go",
			LineNumbers: true,
			Code: `func TextBlock(ctx RenderContext, data TextBlockData) string {
	style := ctx.Theme.Resolve(data.Style)
	if ctx.Width > 0 {
		style = style.Width(ctx.Width)
	}
	return style.Render(data.Text)
}`,
		}))

		parts = append(parts, atoms.CodeBlock(ctx, atoms.CodeBlockData{
			Language: "python",
			FilePath: "src/features/agent_service.py",
			Code: `class AgentService(BaseService[Agent]):
    """Manages agent lifecycle and configuration."""

    async def create(self, name: str, role: str) -> Agent:
        return await self.repo.create(Agent(name=name, role=role))`,
		}))

		raw(strings.Join(parts, "\n"))
	}

	// Table
	{
		var parts []string
		parts = append(parts, section("Table", "Markdown-style tables with aligned columns and rounded borders."))

		parts = append(parts, atoms.Table(ctx, atoms.TableData{
			Headers: []string{"Component", "Type", "Tests", "Status"},
			Rows: [][]string{
				{"TextBlock", "Atom", "4", "done"},
				{"Badge", "Atom", "6", "done"},
				{"Spinner", "Atom", "7", "done"},
				{"MessageBlock", "Molecule", "5", "done"},
				{"ToolCallBlock", "Molecule", "9", "done"},
				{"DiffBlock", "Molecule", "8", "done"},
			},
			Alignments: []atoms.TableAlignment{
				atoms.AlignLeft, atoms.AlignLeft, atoms.AlignRight, atoms.AlignCenter,
			},
		}))

		raw(strings.Join(parts, "\n"))
	}

	// ── Molecules ──────────────────────────────────────────────

	// MessageBlock
	{
		var parts []string
		parts = append(parts, section("MessageBlock", "Chat messages with role badge and indented content."))
		parts = append(parts, "")
		parts = append(parts, molecules.MessageBlock(ctx, molecules.MessageBlockData{
			Role:    atoms.RoleUser,
			Content: "Show me the component inventory.",
		}))
		parts = append(parts, "")
		parts = append(parts, molecules.MessageBlock(ctx, molecules.MessageBlockData{
			Role:    atoms.RoleAssistant,
			Content: "Here are all 15 components across 2 layers.",
		}))
		parts = append(parts, "")
		parts = append(parts, molecules.MessageBlock(ctx, molecules.MessageBlockData{
			Role:    atoms.RoleSystem,
			Content: "Conversation branched from exchange #3.",
		}))

		raw(strings.Join(parts, "\n"))
	}

	// Header
	{
		var parts []string
		parts = append(parts, section("Header", "Page or section title with optional badges and separator."))
		parts = append(parts, "")
		parts = append(parts, molecules.Header(ctx, molecules.HeaderData{
			Title: "CHAT",
			Badges: []atoms.BadgeData{
				{Label: "agent: Code Assistant", Style: theme.Style{Category: theme.CatAgent}, Variant: atoms.BadgeOutline},
				{Label: "5 exchanges", Style: theme.Style{Hierarchy: theme.Tertiary}, Variant: atoms.BadgeOutline},
				{Label: "branch", Style: theme.Style{Category: theme.CatAgent}, Variant: atoms.BadgeOutline},
			},
		}))

		raw(strings.Join(parts, "\n"))
	}

	// ErrorBlock
	{
		var parts []string
		parts = append(parts, section("ErrorBlock", "Error display with badge, message, and recovery suggestions."))
		parts = append(parts, "")
		parts = append(parts, molecules.ErrorBlock(ctx, molecules.ErrorBlockData{
			Title:   "connection failed",
			Message: "Could not reach backend at localhost:8000. The server may not be running.",
			Suggestions: []string{
				"Run 'pts dev' to start the development environment",
				"Check if port 8000 is already in use",
				"Set SB_BACKEND_URL if running the backend elsewhere",
			},
		}))

		raw(strings.Join(parts, "\n"))
	}

	// StatusBar
	{
		var parts []string
		parts = append(parts, section("StatusBar", "Bottom bar with keyboard hints and service health indicator."))
		parts = append(parts, "")

		for _, health := range []struct {
			state molecules.HealthState
			label string
		}{
			{molecules.HealthHealthy, "Healthy"},
			{molecules.HealthStarting, "Starting"},
			{molecules.HealthUnhealthy, "Unhealthy"},
			{molecules.HealthUnknown, "Unknown"},
		} {
			bar := molecules.StatusBar(ctx, molecules.StatusBarData{
				Hints:       " enter: send  pgup/pgdn: scroll  esc: back",
				ServiceName: "backend",
				Health:      health.state,
			})
			label := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text:  "  " + health.label + ":",
				Style: theme.Style{Hierarchy: theme.Tertiary},
			})
			parts = append(parts, label)
			parts = append(parts, bar)
		}

		raw(strings.Join(parts, "\n"))
	}

	// StatusBlock (with static spinner frame)
	{
		var parts []string
		parts = append(parts, section("StatusBlock", "Spinner with verb label and optional elapsed/count badges."))
		parts = append(parts, "")

		spinner := atoms.NewSpinner(99, theme.Style{Category: theme.CatAgent})

		parts = append(parts, "  "+molecules.StatusBlock(ctx, molecules.StatusBlockData{
			Spinner: spinner,
			Verb:    "Reading files",
			Elapsed: 3.2,
			Count:   12,
			Unit:    "files",
		}))
		parts = append(parts, "  "+molecules.StatusBlock(ctx, molecules.StatusBlockData{
			Spinner: spinner,
			Verb:    "Analyzing dependencies",
			Elapsed: 1.7,
		}))
		parts = append(parts, "  "+molecules.StatusBlock(ctx, molecules.StatusBlockData{
			Spinner: spinner,
			Verb:    "Running tests",
			Count:   47,
			Unit:    "passed",
		}))
		parts = append(parts, "  "+molecules.StatusBlock(ctx, molecules.StatusBlockData{
			Spinner: spinner,
			Verb:    "Thinking",
		}))

		raw(strings.Join(parts, "\n"))
	}

	// ToolCallBlock
	{
		var parts []string
		parts = append(parts, section("ToolCallBlock", "Tool invocation display with state icon, name badge, args, and result."))
		parts = append(parts, "")

		spinner := atoms.NewSpinner(100, theme.Style{Status: theme.Running})

		parts = append(parts, "  "+molecules.ToolCallBlock(ctx, molecules.ToolCallBlockData{
			ToolName: "Read",
			Args:     "app/cli/internal/ui/theme/tokens.go",
			State:    molecules.ToolCallSuccess,
			Result:   "52 lines",
		}))
		parts = append(parts, "")
		parts = append(parts, "  "+molecules.ToolCallBlock(ctx, molecules.ToolCallBlockData{
			ToolName: "Edit",
			Args:     "app/cli/internal/chat/view.go",
			State:    molecules.ToolCallRunning,
			Spinner:  spinner,
		}))
		parts = append(parts, "")
		parts = append(parts, "  "+molecules.ToolCallBlock(ctx, molecules.ToolCallBlockData{
			ToolName: "Bash",
			Args:     "go test ./...",
			State:    molecules.ToolCallError,
			Result:   "FAIL: TestBadge_Truncation (badge_test.go:42)",
		}))
		parts = append(parts, "")
		parts = append(parts, "  "+molecules.ToolCallBlock(ctx, molecules.ToolCallBlockData{
			ToolName: "Grep",
			Args:     "pattern: theme.Resolve",
			State:    molecules.ToolCallPending,
		}))

		raw(strings.Join(parts, "\n"))
	}

	// DiffBlock
	{
		var parts []string
		parts = append(parts, section("DiffBlock", "Color-coded unified diff with file path header."))
		parts = append(parts, "")

		parts = append(parts, molecules.DiffBlock(ctx, molecules.DiffBlockData{
			FilePath: "app/cli/internal/chat/view.go",
			Diff: `@@ -146,8 +146,13 @@ func renderMessage(msg Message, width int) string {
 func renderMessage(msg Message, width int) string {
+	// Raw messages are pre-rendered — display as-is.
+	if msg.Raw {
+		return msg.Content
+	}
+
 	ctx := atoms.DefaultContext(width)

 	switch msg.Role {
-	case RoleUser:
-		return renderUserMsg(ctx, msg)
+	case RoleUser:
+		return molecules.MessageBlock(ctx, molecules.MessageBlockData{
+			Role: atoms.RoleUser, Content: msg.Content,
+		})`,
		}))

		raw(strings.Join(parts, "\n"))
	}

	// ConfirmPrompt
	{
		var parts []string
		parts = append(parts, section("ConfirmPrompt", "Binary yes/no choice for agent approval flows."))
		parts = append(parts, "")

		parts = append(parts, "  "+molecules.ConfirmPrompt(ctx, molecules.ConfirmPromptData{
			Question: "Allow agent to run bash command?",
			Selected: true,
		}))
		parts = append(parts, "")
		parts = append(parts, "  "+molecules.ConfirmPrompt(ctx, molecules.ConfirmPromptData{
			Question: "Delete 3 unused files?",
			Selected: false,
		}))

		raw(strings.Join(parts, "\n"))
	}

	// RadioSelect
	{
		var parts []string
		parts = append(parts, section("RadioSelect", "List selection with cursor for picking agents, models, or actions."))
		parts = append(parts, "")

		parts = append(parts, molecules.RadioSelect(ctx, molecules.RadioSelectData{
			Label: "Select an agent:",
			Options: []molecules.RadioOption{
				{Label: "Code Assistant", Description: "General-purpose coding agent"},
				{Label: "Architect", Description: "System design and planning"},
				{Label: "Reviewer", Description: "Code review and quality gates"},
				{Label: "Browser Pilot", Description: "Web interaction and verification"},
			},
			Selected: 1,
		}))

		raw(strings.Join(parts, "\n"))
	}

	return msgs
}
