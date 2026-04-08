package theme

import (
	"fmt"
	"image/color"
	"os"

	"charm.land/lipgloss/v2"
	"gopkg.in/yaml.v3"
)

// themeYAML is the YAML representation of a theme file.
type themeYAML struct {
	Name       string            `yaml:"name"`
	Foreground string            `yaml:"foreground"`
	Background string            `yaml:"background"`
	Dim        string            `yaml:"dim"`
	Categories map[string]string `yaml:"categories"`
	Statuses   map[string]string `yaml:"statuses"`
}

// categoryKeys maps YAML keys to Category indices.
var categoryKeys = map[string]Category{
	"agent":  CatAgent,
	"system": CatSystem,
	"tool":   CatTool,
	"user":   CatUser,
	"cat5":   Cat5,
	"cat6":   Cat6,
	"cat7":   Cat7,
	"cat8":   Cat8,
}

// statusKeys maps YAML keys to Status indices.
var statusKeys = map[string]Status{
	"none":    NoStatus,
	"success": Success,
	"error":   Error,
	"warning": Warning,
	"info":    Info,
	"muted":   Muted,
	"running": Running,
}

func hex(s string) color.Color {
	return lipgloss.Color(s)
}

// LoadThemeFromYAML parses YAML bytes into a Theme.
func LoadThemeFromYAML(data []byte) (*Theme, error) {
	var raw themeYAML
	if err := yaml.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("parse theme YAML: %w", err)
	}

	t := &Theme{
		Name:       raw.Name,
		Foreground: hex(raw.Foreground),
		Background: hex(raw.Background),
		DimColor:   hex(raw.Dim),
	}

	for key, val := range raw.Categories {
		idx, ok := categoryKeys[key]
		if !ok {
			// Skip unknown categories (e.g. "default" from older theme files)
			continue
		}
		t.Categories[idx] = hex(val)
	}

	for key, val := range raw.Statuses {
		idx, ok := statusKeys[key]
		if !ok {
			return nil, fmt.Errorf("unknown status %q", key)
		}
		t.Statuses[idx] = hex(val)
	}

	return t, nil
}

// LoadThemeFile reads a YAML theme from an external file path.
func LoadThemeFile(path string) (*Theme, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read theme file: %w", err)
	}
	return LoadThemeFromYAML(data)
}
