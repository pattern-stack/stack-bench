package molecules

import (
	"github.com/dugshub/agent-tui/internal/ui/components/atoms"
	"github.com/dugshub/agent-tui/internal/ui/theme"
)

// HealthState represents the health of a service.
type HealthState int

const (
	HealthUnknown   HealthState = iota
	HealthStarting
	HealthHealthy
	HealthUnhealthy
)

// StatusBarData holds parameters for rendering a status bar.
type StatusBarData struct {
	Hints       string
	ServiceName string
	Health      HealthState
}

// StatusBar renders a bottom status bar with hints, service name, and health indicator.
func StatusBar(ctx atoms.RenderContext, data StatusBarData) string {
	sep := atoms.Separator(ctx)

	// Status bar elements render inline (no width padding)
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	hints := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
		Text:  data.Hints,
		Style: theme.Style{Hierarchy: theme.Tertiary},
	})

	dot := atoms.Icon(inlineCtx, atoms.IconDot, theme.Style{Status: healthStatus(data.Health)})

	service := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
		Text:  data.ServiceName,
		Style: theme.Style{Hierarchy: theme.Tertiary},
	})

	return sep + "\n" + hints + "  " + dot + " " + service
}

// healthStatus maps a HealthState to a theme Status for coloring.
func healthStatus(h HealthState) theme.Status {
	switch h {
	case HealthHealthy:
		return theme.Success
	case HealthUnhealthy:
		return theme.Error
	case HealthStarting:
		return theme.Warning
	default:
		return theme.Muted
	}
}
