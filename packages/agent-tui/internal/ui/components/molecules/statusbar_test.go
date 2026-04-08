package molecules

import (
	"strings"
	"testing"
)

func TestStatusBar_ContainsSeparator(t *testing.T) {
	out := StatusBar(darkCtx(), StatusBarData{
		Hints:       "ctrl+c quit",
		ServiceName: "backend",
		Health:      HealthHealthy,
	})
	if !strings.Contains(out, "─") {
		t.Error("expected status bar to contain separator")
	}
}

func TestStatusBar_ContainsHints(t *testing.T) {
	out := StatusBar(darkCtx(), StatusBarData{
		Hints:       "ctrl+c quit",
		ServiceName: "backend",
		Health:      HealthHealthy,
	})
	if !strings.Contains(out, "ctrl+c quit") {
		t.Error("expected status bar to contain hints")
	}
}

func TestStatusBar_ContainsServiceName(t *testing.T) {
	out := StatusBar(darkCtx(), StatusBarData{
		Hints:       "hints",
		ServiceName: "my-service",
		Health:      HealthHealthy,
	})
	if !strings.Contains(out, "my-service") {
		t.Error("expected status bar to contain service name")
	}
}

func TestStatusBar_HealthStatesRenderDifferently(t *testing.T) {
	healthy := StatusBar(darkCtx(), StatusBarData{
		Hints: "hints", ServiceName: "svc", Health: HealthHealthy,
	})
	unhealthy := StatusBar(darkCtx(), StatusBarData{
		Hints: "hints", ServiceName: "svc", Health: HealthUnhealthy,
	})
	if healthy == unhealthy {
		t.Error("expected HealthHealthy and HealthUnhealthy to render differently")
	}
}

func TestStatusBar_LightTheme(t *testing.T) {
	out := StatusBar(lightCtx(), StatusBarData{
		Hints:       "hints",
		ServiceName: "svc",
		Health:      HealthStarting,
	})
	if !strings.Contains(out, "svc") {
		t.Error("expected light theme status bar to contain service name")
	}
}
