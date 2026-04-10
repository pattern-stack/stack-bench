package chat

import (
	"fmt"
	"strings"
	"time"

	"charm.land/lipgloss/v2"
	"github.com/alecthomas/chroma/v2/lexers"

	"github.com/dugshub/agentic-tui/internal/ui"
	"github.com/dugshub/agentic-tui/internal/ui/components/atoms"
	"github.com/dugshub/agentic-tui/internal/ui/components/molecules"
	"github.com/dugshub/agentic-tui/internal/ui/theme"
)

// View renders the chat content area: viewport + status line + input.
// The app owns header (above) and legend (below).
func (m *Model) View() string {
	if m.width < 20 || m.height < 4 {
		return ""
	}

	ctx := atoms.DefaultContext(m.width)
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	// Calculate dynamic chrome heights before rendering the viewport.
	// Autocomplete and multiline input both consume vertical space.
	acView := m.autocomplete.View()
	acH := 0
	if acView != "" {
		acH = lipgloss.Height(acView)
	}

	// Input: build wrapped lines to know how tall the input area is.
	sep := atoms.Separator(ctx)
	label := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
		Text:  "you:",
		Style: theme.Style{Hierarchy: theme.Tertiary},
	})
	prefix := " " + label + " "
	prefixW := lipgloss.Width(prefix)
	availW := m.width - prefixW
	if availW < 10 {
		availW = 10
	}
	inputLines := strings.Split(m.input+"_", "\n")
	var wrappedLines []string
	for _, line := range inputLines {
		wrappedLines = append(wrappedLines, wrapLine(line, availW)...)
	}
	extraInputLines := len(wrappedLines) - 1

	// Temporarily shrink viewport for autocomplete + extra input lines.
	chromeExtra := acH + extraInputLines
	if chromeExtra > 0 {
		origH := m.viewport.Height()
		adjusted := origH - chromeExtra
		if adjusted < 1 {
			adjusted = 1
		}
		m.viewport.SetHeight(adjusted)
		defer m.viewport.SetHeight(origH)
	}

	// Viewport
	body := m.viewport.View()

	// Status line
	var statusContent string
	if m.streaming {
		statusContent = atoms.TextBlock(inlineCtx, atoms.TextBlockData{
			Text:  "  ...",
			Style: theme.Style{Category: theme.CatAgent, Status: theme.Running},
		})
	}
	if !m.viewport.AtBottom() && len(m.messages) > 0 {
		pct := int(m.viewport.ScrollPercent() * 100)
		scrollInd := lipgloss.NewStyle().
			Foreground(lipgloss.Color("241")).
			Render(fmt.Sprintf("↑ %d%%", pct))
		pad := m.width - lipgloss.Width(statusContent) - lipgloss.Width(scrollInd) - 2
		if pad < 0 {
			pad = 0
		}
		statusContent += strings.Repeat(" ", pad) + scrollInd
	}

	// Render input lines: first gets the label, rest get padding.
	linePad := strings.Repeat(" ", prefixW)
	var inputRendered []string
	for i, line := range wrappedLines {
		rendered := atoms.TextBlock(inlineCtx, atoms.TextBlockData{Text: line})
		if i == 0 {
			inputRendered = append(inputRendered, prefix+rendered)
		} else {
			inputRendered = append(inputRendered, linePad+rendered)
		}
	}
	inputLine := sep + "\n" + strings.Join(inputRendered, "\n")

	// Compose final output.
	if acView != "" {
		return body + "\n" + acView + "\n" + statusContent + "\n" + inputLine
	}
	return body + "\n" + statusContent + "\n" + inputLine
}

// RenderHeader returns the chat header for the app to compose.
func (m *Model) RenderHeader() string {
	ctx := atoms.DefaultContext(m.width)

	agent := m.agentName
	if agent == "" {
		agent = "no agent"
	}

	badges := []atoms.BadgeData{
		{
			Label:   "agent: " + agent,
			Style:   theme.Style{Category: theme.CatAgent},
			Variant: atoms.BadgeOutline,
		},
	}

	if m.ExchangeCount > 0 {
		badges = append(badges, atoms.BadgeData{
			Label:   fmt.Sprintf("%d exchanges", m.ExchangeCount),
			Style:   theme.Style{Hierarchy: theme.Tertiary},
			Variant: atoms.BadgeOutline,
		})
	}

	if m.IsBranch {
		badges = append(badges, atoms.BadgeData{
			Label:   "branch",
			Style:   theme.Style{Category: theme.CatAgent},
			Variant: atoms.BadgeOutline,
		})
	}

	return molecules.Header(ctx, molecules.HeaderData{
		Title:  "CHAT",
		Badges: badges,
	})
}

// spinnerSet bundles the chat model's two active spinners so we can pass
// them through the render pipeline as a single unit.
type spinnerSet struct {
	tool     atoms.Spinner
	thinking atoms.Spinner
}

func renderMessage(msg Message, width int, spinners spinnerSet, isLastMessage bool) string {
	// Raw messages are pre-rendered — display as-is.
	if msg.Raw {
		return msg.RawContent
	}

	ctx := atoms.DefaultContext(width)

	switch msg.Role {
	case RoleUser:
		return molecules.MessageBlock(ctx, molecules.MessageBlockData{
			Role:    atoms.RoleUser,
			Content: msg.Content(),
		})

	case RoleAssistant:
		return renderAssistantMessage(ctx, msg, width, spinners, isLastMessage)

	case RoleSystem:
		return molecules.MessageBlock(ctx, molecules.MessageBlockData{
			Role:    atoms.RoleSystem,
			Content: msg.Content(),
		})
	}
	return ""
}

func renderAssistantMessage(ctx atoms.RenderContext, msg Message, width int, spinners spinnerSet, isLastMessage bool) string {
	badge := atoms.Badge(ctx, atoms.BadgeData{
		Label:   "assistant",
		Style:   theme.Style{Category: theme.CatAgent},
		Variant: atoms.BadgeFilled,
	})

	contentWidth := width - 4
	if contentWidth < 20 {
		contentWidth = 20
	}

	var sections []string
	sections = append(sections, badge)

	var prevType PartType
	for i, part := range msg.Parts {
		// A thinking part is "actively streaming" if this is the last part
		// of the last (assistant) message and it hasn't been marked Complete.
		// That's the only part that should show the live thinking spinner.
		isLastPart := isLastMessage && i == len(msg.Parts)-1
		active := isLastPart && !part.Complete
		rendered := renderPart(ctx, part, contentWidth, spinners, active)
		if rendered != "" {
			lines := strings.Split(rendered, "\n")
			indented := "  " + strings.Join(lines, "\n  ")
			// Add blank line between parts of different types
			if prevType != "" && prevType != part.Type {
				sections = append(sections, "")
			}
			sections = append(sections, indented)
			prevType = part.Type
		}
	}

	if len(sections) == 1 {
		return badge
	}

	return strings.Join(sections, "\n")
}

func renderPart(ctx atoms.RenderContext, part MessagePart, contentWidth int, spinners spinnerSet, active bool) string {
	switch part.Type {
	case PartText:
		if part.Content == "" {
			return ""
		}
		return ui.RenderMarkdown(part.Content, contentWidth)

	case PartThinking:
		if part.Content == "" {
			return ""
		}
		summary := part.Content
		if idx := strings.IndexByte(summary, '\n'); idx > 0 {
			summary = summary[:idx]
		}
		if len(summary) > 60 {
			summary = summary[:57] + "..."
		}
		// Prefix with the Star spinner when actively streaming, otherwise
		// a static dim glyph so completed thinking still reads as a block.
		inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}
		var prefix string
		if active {
			prefix = spinners.thinking.View(inlineCtx) + " "
		} else {
			prefix = atoms.TextBlock(inlineCtx, atoms.TextBlockData{
				Text:  "·",
				Style: theme.Style{Hierarchy: theme.Tertiary},
			}) + " "
		}
		body := atoms.TextBlock(ctx, atoms.TextBlockData{
			Text:  "thinking: " + summary,
			Style: theme.Style{Hierarchy: theme.Tertiary},
		})
		return prefix + body

	case PartToolCall:
		return renderToolCallPart(ctx, part, spinners.tool)

	case PartError:
		return molecules.ErrorBlock(ctx, molecules.ErrorBlockData{
			Message: part.Content,
		})
	}
	return ""
}

// graduateSpinner picks a spinner frame set based on how long a tool call
// has been running. Short runs use the subtle default; longer runs escalate
// to progressively more attention-grabbing animations so a stuck or slow
// tool becomes visually obvious without having to surface a timer.
func graduateSpinner(base atoms.Spinner, elapsed time.Duration) atoms.Spinner {
	switch {
	case elapsed < 5*time.Second:
		// keep the default (SparseCenter — subtle)
	case elapsed < 15*time.Second:
		base.Frames = atoms.SpinnerPulse
	default:
		base.Frames = atoms.SpinnerHeartbeat
	}
	return base
}

func renderToolCallPart(ctx atoms.RenderContext, part MessagePart, spinner atoms.Spinner) string {
	tc := part.ToolCall
	if tc == nil {
		return ""
	}

	// Map chat ToolCallState to molecules ToolCallState
	var state molecules.ToolCallState
	switch tc.State {
	case ToolCallStatePending:
		state = molecules.ToolCallPending
	case ToolCallStateRunning:
		state = molecules.ToolCallRunning
		if !tc.StartedAt.IsZero() {
			spinner = graduateSpinner(spinner, time.Since(tc.StartedAt))
		}
	case ToolCallStateComplete:
		state = molecules.ToolCallSuccess
	case ToolCallStateError:
		state = molecules.ToolCallError
	}

	result := tc.Result
	if tc.Error != "" {
		result = tc.Error
	}

	// For rich display types, hide args (they're noisy and the body shows context).
	// For generic, show args inline.
	hideArgs := tc.State == ToolCallStateComplete && result != "" &&
		(tc.DisplayType == "diff" || tc.DisplayType == "code" || tc.DisplayType == "bash")
	args := ""
	if !hideArgs {
		args = formatArgs(tc.Arguments)
	}

	// Render the tool call header (icon + name badge + args)
	header := molecules.ToolCallBlock(ctx, molecules.ToolCallBlockData{
		ToolName: tc.Name,
		State:    state,
		Spinner:  spinner,
		Args:     args,
	})

	// While running or no result, just show the header (and error text if any)
	if tc.State != ToolCallStateComplete || result == "" {
		if result != "" {
			return header + "\n" + indentBody(result)
		}
		return header
	}

	// Dispatch by display_type for completed successful tool calls
	switch tc.DisplayType {
	case "diff":
		path, _ := tc.Arguments["path"].(string)
		body := molecules.DiffBlock(ctx, molecules.DiffBlockData{
			FilePath: path,
			Hunks:    molecules.ParseUnifiedDiff(result),
			Language: languageFromPath(path),
		})
		return header + "\n" + indentBody(body)

	case "code":
		path, _ := tc.Arguments["path"].(string)
		body := atoms.CodeBlock(ctx, atoms.CodeBlockData{
			Code:     result,
			FilePath: path,
			Language: languageFromPath(path),
		})
		return header + "\n" + indentBody(body)

	case "bash":
		body := atoms.CodeBlock(ctx, atoms.CodeBlockData{
			Code:     result,
			Language: "bash",
		})
		return header + "\n" + indentBody(body)

	default:
		return header + "\n" + indentBody(result)
	}
}

// indentBody nests a tool body under its header. Returns the body unchanged
// so code/diff blocks can use the full available width rather than losing
// columns to decorative indentation — the tool header on its own line above
// already provides sufficient visual association.
func indentBody(s string) string {
	return s
}

// languageFromPath returns a chroma-compatible language name based on the
// filename, using chroma's built-in extension matching (covers ~250 languages).
func languageFromPath(path string) string {
	if path == "" {
		return ""
	}
	lexer := lexers.Match(path)
	if lexer == nil {
		return ""
	}
	return lexer.Config().Name
}
