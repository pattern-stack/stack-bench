package chat

import "strings"

// Input editing operations. Extracted so they can be reused
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
