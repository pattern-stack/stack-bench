package cliclient

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"

	"github.com/dugshub/agentic-tui/internal/types"
)

// Compile-time check that Client implements types.Client.
var _ types.Client = (*Client)(nil)

// Format identifies the JSONL output format of a CLI agent.
type Format string

const (
	FormatClaude Format = "claude"
	FormatGemini Format = "gemini"
)

// Config configures a CLI agent transport.
type Config struct {
	Command string
	Args    []string
	Format  Format
	Dir     string
	Env     []string
}

// Parser translates a JSONL line into zero or more StreamChunks.
type Parser interface {
	ParseLine(line []byte) []types.StreamChunk
}

// Client spawns a CLI agent per message and parses its JSONL output.
type Client struct {
	command string
	args    []string
	parser  Parser
	dir     string
	env     []string
}

// New creates a CLI agent client.
func New(cfg Config) *Client {
	var parser Parser
	switch cfg.Format {
	case FormatGemini:
		parser = &GeminiParser{}
	default:
		parser = &ClaudeParser{}
	}

	return &Client{
		command: cfg.Command,
		args:    cfg.Args,
		parser:  parser,
		dir:     cfg.Dir,
		env:     cfg.Env,
	}
}

// ListAgents returns a single agent representing this CLI tool.
func (c *Client) ListAgents(ctx context.Context) ([]types.AgentSummary, error) {
	return []types.AgentSummary{
		{ID: c.command, Name: c.command, Role: "CLI agent"},
	}, nil
}

// CreateConversation returns a generated conversation ID.
func (c *Client) CreateConversation(ctx context.Context, agentID string) (string, error) {
	return fmt.Sprintf("cli-%d", os.Getpid()), nil
}

// SendMessage spawns the CLI, parses JSONL output, and emits StreamChunks.
func (c *Client) SendMessage(ctx context.Context, conversationID string, content string) (<-chan types.StreamChunk, error) {
	// Build command: base args + user message
	args := make([]string, len(c.args))
	copy(args, c.args)
	args = append(args, content)

	cmd := exec.CommandContext(ctx, c.command, args...)
	if c.dir != "" {
		cmd.Dir = c.dir
	}
	if len(c.env) > 0 {
		cmd.Env = append(os.Environ(), c.env...)
	}
	cmd.Stderr = os.Stderr

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, fmt.Errorf("stdout pipe: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("start %s: %w", c.command, err)
	}

	ch := make(chan types.StreamChunk, 16)

	go func() {
		defer close(ch)

		scanner := bufio.NewScanner(stdout)
		// Allow large lines (some tool outputs can be big)
		scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)

		for scanner.Scan() {
			line := scanner.Bytes()
			if len(line) == 0 {
				continue
			}
			chunks := c.parser.ParseLine(line)
			for _, chunk := range chunks {
				ch <- chunk
			}
		}

		_ = cmd.Wait()

		ch <- types.StreamChunk{Done: true, Type: types.ChunkText}
	}()

	return ch, nil
}

// ListConversations is not supported for CLI agents.
func (c *Client) ListConversations(ctx context.Context, agentName string) ([]types.Conversation, error) {
	return nil, nil
}

// GetConversation is not supported for CLI agents.
func (c *Client) GetConversation(ctx context.Context, id string) (*types.ConversationDetailResponse, error) {
	return nil, nil
}
