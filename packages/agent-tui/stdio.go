package tui

// StdioConfig configures a JSON-RPC over stdio backend connection.
type StdioConfig struct {
	Command string
	Args    []string
	Dir     string
	Env     []string
}

// NewStdioClient creates a Client that communicates via JSON-RPC over stdin/stdout.
func NewStdioClient(cfg StdioConfig) (Client, error) {
	return newStdioClient(cfg)
}
