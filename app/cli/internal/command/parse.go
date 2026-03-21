package command

import "strings"

// ParseResult holds the parsed output of a slash command.
type ParseResult struct {
	Command string
	Args    []string
	Flags   map[string]bool
	Options map[string]string
	Raw     string
}

// Parse splits a slash command input into its parts.
// Input must start with "/". Returns a ParseResult with the command name
// (without slash), positional args, flags (-f), and options (--key=val or --key val).
func Parse(input string) ParseResult {
	raw := input
	input = strings.TrimPrefix(input, "/")

	tokens := tokenize(input)
	result := ParseResult{
		Raw:     raw,
		Flags:   make(map[string]bool),
		Options: make(map[string]string),
	}

	if len(tokens) == 0 {
		return result
	}

	result.Command = strings.ToLower(tokens[0])

	i := 1
	for i < len(tokens) {
		tok := tokens[i]

		if strings.HasPrefix(tok, "--") {
			key := strings.TrimPrefix(tok, "--")
			if eqIdx := strings.Index(key, "="); eqIdx >= 0 {
				result.Options[key[:eqIdx]] = key[eqIdx+1:]
			} else if i+1 < len(tokens) && !strings.HasPrefix(tokens[i+1], "-") {
				result.Options[key] = tokens[i+1]
				i++
			} else {
				result.Flags[key] = true
			}
		} else if strings.HasPrefix(tok, "-") {
			flag := strings.TrimPrefix(tok, "-")
			result.Flags[flag] = true
		} else {
			result.Args = append(result.Args, tok)
		}

		i++
	}

	return result
}

// tokenize splits input respecting quoted strings.
func tokenize(input string) []string {
	var tokens []string
	var current strings.Builder
	inQuote := false
	quoteChar := byte(0)

	for i := 0; i < len(input); i++ {
		ch := input[i]

		if inQuote {
			if ch == quoteChar {
				inQuote = false
			} else {
				current.WriteByte(ch)
			}
			continue
		}

		if ch == '"' || ch == '\'' {
			inQuote = true
			quoteChar = ch
			continue
		}

		if ch == ' ' || ch == '\t' {
			if current.Len() > 0 {
				tokens = append(tokens, current.String())
				current.Reset()
			}
			continue
		}

		current.WriteByte(ch)
	}

	if current.Len() > 0 {
		tokens = append(tokens, current.String())
	}

	return tokens
}
