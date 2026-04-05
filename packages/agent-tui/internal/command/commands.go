package command

import tea "charm.land/bubbletea/v2"

// ClearMsg signals the chat to clear its history.
type ClearMsg struct{}

// SwitchAgentMsg signals a return to agent selection.
type SwitchAgentMsg struct{}

// ShowHelpMsg signals the chat to display command help.
type ShowHelpMsg struct {
	Commands []Def
}

// DefaultRegistry returns a registry pre-loaded with built-in commands.
func DefaultRegistry() *Registry {
	r := NewRegistry()

	r.Register(Def{
		Name:        "help",
		Aliases:     []string{"h", "?"},
		Description: "Show available commands",
		Category:    "general",
		Handler: func(_ ParseResult) tea.Cmd {
			cmds := r.List("")
			return func() tea.Msg { return ShowHelpMsg{Commands: cmds} }
		},
	})

	r.Register(Def{
		Name:        "clear",
		Aliases:     []string{"c"},
		Description: "Clear chat history",
		Category:    "general",
		Handler: func(_ ParseResult) tea.Cmd {
			return func() tea.Msg { return ClearMsg{} }
		},
	})

	r.Register(Def{
		Name:        "agents",
		Aliases:     []string{"a"},
		Description: "Switch to a different agent",
		Category:    "navigation",
		Handler: func(_ ParseResult) tea.Cmd {
			return func() tea.Msg { return SwitchAgentMsg{} }
		},
	})

	r.Register(Def{
		Name:        "quit",
		Aliases:     []string{"q"},
		Description: "Exit the application",
		Category:    "general",
		Handler: func(_ ParseResult) tea.Cmd {
			return tea.Quit
		},
	})

	return r
}
