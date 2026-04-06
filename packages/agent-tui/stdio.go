package tui

// StdioConfig configures a JSON-RPC over stdio backend connection.
type StdioConfig struct {
	Command string
	Args    []string
	Dir     string
	Env     []string
}
