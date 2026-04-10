package execclient

import (
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"

	"github.com/dugshub/agentic-tui/internal/types"
)

// Compile-time check that Client implements types.Client.
var _ types.Client = (*Client)(nil)

// Config configures a raw text CLI transport.
type Config struct {
	Command        string
	Args           []string
	Dir            string
	Env            []string
	PromptViaStdin bool
}

// Client spawns a CLI command per message and streams stdout as plain text.
type Client struct {
	command        string
	args           []string
	dir            string
	env            []string
	promptViaStdin bool
}

// New creates an exec client.
func New(cfg Config) *Client {
	return &Client{
		command:        cfg.Command,
		args:           cfg.Args,
		dir:            cfg.Dir,
		env:            cfg.Env,
		promptViaStdin: cfg.PromptViaStdin,
	}
}

// ListAgents returns a single agent representing this CLI tool.
func (c *Client) ListAgents(ctx context.Context) ([]types.AgentSummary, error) {
	return []types.AgentSummary{
		{ID: c.command, Name: c.command, Role: "CLI tool"},
	}, nil
}

// CreateConversation returns a generated conversation ID.
func (c *Client) CreateConversation(ctx context.Context, agentID string) (string, error) {
	return fmt.Sprintf("exec-%d", os.Getpid()), nil
}

// SendMessage spawns the command, reads stdout in chunks, and emits StreamChunks.
func (c *Client) SendMessage(ctx context.Context, conversationID string, content string) (<-chan types.StreamChunk, error) {
	var args []string
	args = append(args, c.args...)
	if !c.promptViaStdin {
		args = append(args, content)
	}

	cmd := exec.CommandContext(ctx, c.command, args...)
	if c.dir != "" {
		cmd.Dir = c.dir
	}
	if len(c.env) > 0 {
		cmd.Env = append(os.Environ(), c.env...)
	}
	cmd.Stderr = os.Stderr

	if c.promptViaStdin {
		stdin, err := cmd.StdinPipe()
		if err != nil {
			return nil, fmt.Errorf("stdin pipe: %w", err)
		}
		go func() {
			defer stdin.Close()
			io.WriteString(stdin, content)
		}()
	}

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

		buf := make([]byte, 256)
		for {
			n, err := stdout.Read(buf)
			if n > 0 {
				ch <- types.StreamChunk{
					Content: string(buf[:n]),
					Type:    types.ChunkText,
				}
			}
			if err != nil {
				break
			}
		}

		_ = cmd.Wait()

		ch <- types.StreamChunk{Done: true, Type: types.ChunkText}
	}()

	return ch, nil
}

// ListConversations is not supported for exec clients.
func (c *Client) ListConversations(ctx context.Context, agentName string) ([]types.Conversation, error) {
	return nil, nil
}

// GetConversation is not supported for exec clients.
func (c *Client) GetConversation(ctx context.Context, id string) (*types.ConversationDetailResponse, error) {
	return nil, nil
}
