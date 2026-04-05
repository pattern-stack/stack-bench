package command

import (
	"sort"
	"strings"

	tea "charm.land/bubbletea/v2"
)

// Handler is the function signature for command handlers.
// It receives the parsed result and returns a Bubble Tea command.
type Handler func(result ParseResult) tea.Cmd

// Def defines a slash command.
type Def struct {
	Name        string
	Aliases     []string
	Description string
	Category    string
	Hidden      bool
	Handler     Handler
}

// Registry stores and looks up slash commands.
type Registry struct {
	commands map[string]*Def
	aliases  map[string]string
	ordered  []string // insertion order for listing
}

// NewRegistry creates an empty command registry.
func NewRegistry() *Registry {
	return &Registry{
		commands: make(map[string]*Def),
		aliases:  make(map[string]string),
	}
}

// Register adds a command to the registry.
func (r *Registry) Register(def Def) {
	name := strings.ToLower(def.Name)
	r.commands[name] = &def
	r.ordered = append(r.ordered, name)

	for _, alias := range def.Aliases {
		r.aliases[strings.ToLower(alias)] = name
	}
}

// Lookup finds a command by name or alias. Returns nil if not found.
func (r *Registry) Lookup(name string) *Def {
	name = strings.ToLower(name)

	if def, ok := r.commands[name]; ok {
		return def
	}

	if target, ok := r.aliases[name]; ok {
		return r.commands[target]
	}

	return nil
}

// List returns all visible commands, optionally filtered by category.
func (r *Registry) List(category string) []Def {
	var result []Def
	for _, name := range r.ordered {
		def := r.commands[name]
		if def.Hidden {
			continue
		}
		if category != "" && def.Category != category {
			continue
		}
		result = append(result, *def)
	}
	return result
}

// Suggest returns commands matching a partial input, using prefix then fuzzy matching.
func (r *Registry) Suggest(partial string, limit int) []Def {
	partial = strings.ToLower(partial)
	if limit <= 0 {
		limit = 5
	}

	seen := make(map[string]bool)
	var result []Def

	// Pass 1: prefix matches (sorted alphabetically)
	var prefixMatches []string
	for name := range r.commands {
		if strings.HasPrefix(name, partial) && !r.commands[name].Hidden {
			prefixMatches = append(prefixMatches, name)
		}
	}
	sort.Strings(prefixMatches)
	for _, name := range prefixMatches {
		if len(result) >= limit {
			return result
		}
		result = append(result, *r.commands[name])
		seen[name] = true
	}

	// Also check alias prefixes
	for alias, target := range r.aliases {
		if strings.HasPrefix(alias, partial) && !seen[target] && !r.commands[target].Hidden {
			if len(result) >= limit {
				return result
			}
			result = append(result, *r.commands[target])
			seen[target] = true
		}
	}

	// Pass 2: fuzzy matches (Levenshtein distance <= len/3)
	if len(result) < limit {
		maxDist := len(partial) / 3
		if maxDist < 1 {
			maxDist = 1
		}
		for name := range r.commands {
			if seen[name] || r.commands[name].Hidden {
				continue
			}
			if levenshtein(partial, name) <= maxDist {
				result = append(result, *r.commands[name])
				seen[name] = true
				if len(result) >= limit {
					break
				}
			}
		}
	}

	return result
}

// levenshtein computes the edit distance between two strings.
func levenshtein(a, b string) int {
	la, lb := len(a), len(b)
	if la == 0 {
		return lb
	}
	if lb == 0 {
		return la
	}

	prev := make([]int, lb+1)
	curr := make([]int, lb+1)

	for j := 0; j <= lb; j++ {
		prev[j] = j
	}

	for i := 1; i <= la; i++ {
		curr[0] = i
		for j := 1; j <= lb; j++ {
			cost := 1
			if a[i-1] == b[j-1] {
				cost = 0
			}
			del := prev[j] + 1
			ins := curr[j-1] + 1
			sub := prev[j-1] + cost
			curr[j] = min(del, min(ins, sub))
		}
		prev, curr = curr, prev
	}

	return prev[lb]
}
