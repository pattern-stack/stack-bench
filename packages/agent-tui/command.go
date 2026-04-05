package tui

import tea "charm.land/bubbletea/v2"

// CommandDef defines a slash command.
type CommandDef struct {
	Name        string
	Aliases     []string
	Description string
	Category    string
	Hidden      bool
	Handler     CommandHandler
}

// CommandHandler is called when a slash command is executed.
type CommandHandler func(result CommandParseResult) tea.Cmd

// CommandParseResult holds the parsed output of a slash command.
type CommandParseResult struct {
	Command string
	Args    []string
	Flags   map[string]bool
	Options map[string]string
	Raw     string
}
