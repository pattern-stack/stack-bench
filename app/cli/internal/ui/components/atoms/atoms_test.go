package atoms

import (
	"testing"

	"github.com/dugshub/stack-bench/app/cli/internal/ui/theme"
)

// testContext creates a RenderContext with the given theme and width.
func testContext(t *theme.Theme, width int) RenderContext {
	return RenderContext{Width: width, Theme: t}
}

func TestDefaultContext(t *testing.T) {
	ctx := DefaultContext(80)
	if ctx.Width != 80 {
		t.Errorf("expected width 80, got %d", ctx.Width)
	}
	if ctx.Theme == nil {
		t.Error("expected non-nil theme from DefaultContext")
	}
}

func TestRoleConstants(t *testing.T) {
	// Verify roles are distinct
	roles := []Role{RoleUser, RoleAssistant, RoleSystem}
	seen := make(map[Role]bool)
	for _, r := range roles {
		if seen[r] {
			t.Errorf("duplicate role value: %d", r)
		}
		seen[r] = true
	}
}
