package molecules

import (
	"github.com/dugshub/stack-bench/app/cli/internal/ui/components/atoms"
	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// HealthState represents the health of a service.
type HealthState int

const (
	HealthUnknown HealthState = iota
	HealthStarting
	HealthHealthy
	HealthUnhealthy
)

// StatusBarData holds parameters for rendering a status bar. StatusBar is
// deliberately generic — it displays any named service (or logical unit of
// work) with its health state. Spinner is optional; when set and the state
// is "active" (Healthy or Starting), the indicator animates instead of
// showing a static dot.
type StatusBarData struct {
	Hints       string
	ServiceName string
	Health      HealthState
	Spinner     *atoms.Spinner // optional: animated indicator for active states
}

// StatusBar renders a bottom status bar with hints, service name, and
// health indicator.
func StatusBar(ctx atoms.RenderContext, data StatusBarData) string {
	sep := atoms.Separator(ctx)

	// Status bar elements render inline (no width padding)
	inlineCtx := atoms.RenderContext{Width: 0, Theme: ctx.Theme}

	hints := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
		Text:  data.Hints,
		Style: theme.Style{Hierarchy: theme.Tertiary},
	})

	// Choose between animated spinner and static dot. The spinner replaces
	// the dot for "active" states (Healthy/Starting). Color follows the
	// health state so red/amber/green semantics still read at a glance.
	var indicator string
	animatable := data.Spinner != nil && (data.Health == HealthHealthy || data.Health == HealthStarting)
	if animatable {
		sp := *data.Spinner // copy so we can override Style without mutating caller
		sp.Style = theme.Style{Status: healthStatus(data.Health)}
		indicator = sp.View(inlineCtx)
	} else {
		indicator = atoms.Icon(inlineCtx, atoms.IconDot, theme.Style{Status: healthStatus(data.Health)})
	}

	service := atoms.TextBlock(inlineCtx, atoms.TextBlockData{
		Text:  data.ServiceName,
		Style: theme.Style{Hierarchy: theme.Tertiary},
	})

	return sep + "\n" + hints + "  " + indicator + " " + service
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
