package chat

import "strings"

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
	trimmed := strings.TrimRight(s, " ")
	if trimmed == "" {
		return ""
	}
	lastSpace := strings.LastIndex(trimmed, " ")
	if lastSpace < 0 {
		return ""
	}
	return trimmed[:lastSpace+1]
}

// deleteLine clears the entire input.
func deleteLine(_ string) string {
	return ""
}
