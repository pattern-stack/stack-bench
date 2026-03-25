package chat

import (
	"strings"

	"charm.land/lipgloss/v2"
)

// Input editing and layout operations. Extracted so they can be reused
// when we swap the hand-rolled input for a bubbles/textinput.

// deleteChar removes the last character from s.
func deleteChar(s string) string {
	if len(s) == 0 {
		return s
	}
	runes := []rune(s)
	return string(runes[:len(runes)-1])
}

// deleteWord removes the last word (and trailing spaces) from s.
func deleteWord(s string) string {
	if len(s) == 0 {
		return s
	}
	// Trim trailing spaces
	trimmed := strings.TrimRight(s, " ")
	if trimmed == "" {
		return ""
	}
	// Find the last space boundary
	lastSpace := strings.LastIndex(trimmed, " ")
	if lastSpace < 0 {
		return ""
	}
	return trimmed[:lastSpace+1]
}

// deleteLine clears the entire input.
func deleteLine(s string) string {
	_ = s
	return ""
}

// wrapLine breaks a single line into chunks that fit within maxWidth,
// preferring word boundaries over hard character breaks.
func wrapLine(line string, maxWidth int) []string {
	if maxWidth <= 0 || lipgloss.Width(line) <= maxWidth {
		return []string{line}
	}
	runes := []rune(line)
	var result []string
	for len(runes) > 0 {
		if lipgloss.Width(string(runes)) <= maxWidth {
			result = append(result, string(runes))
			break
		}
		breakAt := maxWidth
		if breakAt > len(runes) {
			breakAt = len(runes)
		}
		// Try to break at a space
		best := -1
		for i := breakAt; i > 0; i-- {
			if runes[i-1] == ' ' {
				best = i
				break
			}
		}
		if best > 0 {
			result = append(result, string(runes[:best]))
			runes = runes[best:]
		} else {
			result = append(result, string(runes[:breakAt]))
			runes = runes[breakAt:]
		}
	}
	if len(result) == 0 {
		return []string{""}
	}
	return result
}
