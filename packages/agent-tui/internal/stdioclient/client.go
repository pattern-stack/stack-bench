package stdioclient

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/dugshub/agent-tui/internal/sse"
)

const shutdownTimeout = 5 * time.Second

// Config configures a JSON-RPC over stdio backend connection.
type Config struct {
	Command string
	Args    []string
	Dir     string
	Env     []string
}

// Client communicates with a backend via JSON-RPC over stdin/stdout.
type Client struct {
	cmd    *exec.Cmd
	writer *Writer
	reader *Reader
	stderr io.ReadCloser

	mu       sync.Mutex
	pending  map[int64]chan *Response
	streamCh chan sse.StreamChunk
	closeOnce atomic.Pointer[sync.Once] // guards streamCh close
	closed   bool
}

// New spawns a subprocess and returns a Client.
func New(cfg Config) (*Client, error) {
	cmd := exec.Command(cfg.Command, cfg.Args...)
	if cfg.Dir != "" {
		cmd.Dir = cfg.Dir
	}
	if len(cfg.Env) > 0 {
		cmd.Env = append(os.Environ(), cfg.Env...)
	}

	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, fmt.Errorf("stdin pipe: %w", err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, fmt.Errorf("stdout pipe: %w", err)
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return nil, fmt.Errorf("stderr pipe: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("start subprocess: %w", err)
	}

	c := &Client{
		cmd:     cmd,
		writer:  NewWriter(stdin),
		reader:  NewReader(stdout),
		stderr:  stderr,
		pending: make(map[int64]chan *Response),
	}

	go c.readLoop()

	return c, nil
}

func (c *Client) readLoop() {
	for {
		resp, notif, err := c.reader.ReadMessage()
		if err != nil {
			c.mu.Lock()
			c.closed = true
			// Signal all pending requests
			for _, ch := range c.pending {
				close(ch)
			}
			c.pending = make(map[int64]chan *Response)
			streamCh := c.streamCh
			c.streamCh = nil
			if streamCh != nil {
				if once := c.closeOnce.Load(); once != nil {
					once.Do(func() { close(streamCh) })
				}
			}
			c.mu.Unlock()
			return
		}

		if resp != nil {
			c.mu.Lock()
			ch, ok := c.pending[*resp.ID]
			if ok {
				delete(c.pending, *resp.ID)
			}
			c.mu.Unlock()
			if ok {
				ch <- resp
				close(ch)
			}
		}

		if notif != nil && notif.Method == "stream.event" {
			c.handleStreamEvent(notif)
		}
	}
}

func (c *Client) handleStreamEvent(notif *Notification) {
	var params StreamEventParams
	if err := json.Unmarshal(notif.Params, &params); err != nil {
		return
	}

	c.mu.Lock()
	ch := c.streamCh
	c.mu.Unlock()

	if ch == nil {
		return
	}

	chunk := convertStreamEvent(params)
	if chunk != nil {
		ch <- *chunk
		if chunk.Done {
			c.mu.Lock()
			c.streamCh = nil
			c.mu.Unlock()
			if once := c.closeOnce.Load(); once != nil {
				once.Do(func() { close(ch) })
			}
		}
	}
}

func convertStreamEvent(params StreamEventParams) *sse.StreamChunk {
	switch params.Type {
	case "message.delta":
		var d struct {
			Delta string `json:"delta"`
		}
		if json.Unmarshal(params.Data, &d) != nil {
			return nil
		}
		return &sse.StreamChunk{Content: d.Delta, Type: sse.ChunkText}

	case "message.complete":
		return &sse.StreamChunk{Done: true, Type: sse.ChunkText}

	case "thinking":
		var d struct {
			Content string `json:"content"`
		}
		if json.Unmarshal(params.Data, &d) != nil {
			return nil
		}
		return &sse.StreamChunk{Content: d.Content, Type: sse.ChunkThinking}

	case "tool.start":
		var d struct {
			ID          string `json:"id"`
			Name        string `json:"name"`
			Input       string `json:"input"`
			DisplayType string `json:"display_type"`
		}
		if json.Unmarshal(params.Data, &d) != nil {
			return nil
		}
		return &sse.StreamChunk{
			Content:     d.Name,
			Type:        sse.ChunkToolStart,
			ToolCallID:  d.ID,
			ToolName:    d.Name,
			DisplayType: d.DisplayType,
			ToolInput:   d.Input,
		}

	case "tool.end":
		var d struct {
			ID          string `json:"id"`
			Name        string `json:"name"`
			Output      string `json:"output"`
			Error       string `json:"error"`
			DisplayType string `json:"display_type"`
		}
		if json.Unmarshal(params.Data, &d) != nil {
			return nil
		}
		return &sse.StreamChunk{
			Content:     d.Output,
			Type:        sse.ChunkToolEnd,
			ToolCallID:  d.ID,
			ToolName:    d.Name,
			DisplayType: d.DisplayType,
			ToolError:   d.Error,
		}

	case "error":
		var d struct {
			Type    string `json:"type"`
			Message string `json:"message"`
		}
		if json.Unmarshal(params.Data, &d) != nil {
			return nil
		}
		return &sse.StreamChunk{
			Content: "Error: " + d.Message,
			Done:    true,
			Error:   fmt.Errorf("%s: %s", d.Type, d.Message),
		}

	case "done":
		return &sse.StreamChunk{Done: true, Type: sse.ChunkText}

	default:
		return nil
	}
}

func (c *Client) call(method string, params interface{}) (*Response, error) {
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return nil, fmt.Errorf("client closed")
	}
	c.mu.Unlock()

	id, err := c.writer.WriteRequest(method, params)
	if err != nil {
		return nil, err
	}

	ch := make(chan *Response, 1)
	c.mu.Lock()
	c.pending[id] = ch
	c.mu.Unlock()

	resp, ok := <-ch
	if !ok {
		return nil, fmt.Errorf("connection closed while waiting for response")
	}

	if resp.Error != nil {
		return nil, resp.Error
	}

	return resp, nil
}

// ListAgents sends a listAgents request.
func (c *Client) ListAgents(ctx context.Context) ([]sse.AgentSummary, error) {
	resp, err := c.call("listAgents", nil)
	if err != nil {
		return nil, err
	}

	var agents []sse.AgentSummary
	if err := json.Unmarshal(resp.Result, &agents); err != nil {
		return nil, err
	}
	return agents, nil
}

// CreateConversation sends a createConversation request.
func (c *Client) CreateConversation(ctx context.Context, agentID string) (string, error) {
	params := map[string]string{"agent_id": agentID}
	resp, err := c.call("createConversation", params)
	if err != nil {
		return "", err
	}

	var result struct {
		ID string `json:"id"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		return "", err
	}
	return result.ID, nil
}

// SendMessage sends a sendMessage request and returns a channel of stream chunks.
func (c *Client) SendMessage(ctx context.Context, conversationID string, content string) (<-chan sse.StreamChunk, error) {
	ch := make(chan sse.StreamChunk, 16)
	once := &sync.Once{}

	c.mu.Lock()
	c.streamCh = ch
	c.closeOnce.Store(once)
	c.mu.Unlock()

	params := map[string]string{
		"conversation_id": conversationID,
		"content":         content,
	}

	id, err := c.writer.WriteRequest("sendMessage", params)
	if err != nil {
		c.mu.Lock()
		c.streamCh = nil
		c.mu.Unlock()
		close(ch)
		return nil, err
	}

	// Register pending response handler
	respCh := make(chan *Response, 1)
	c.mu.Lock()
	c.pending[id] = respCh
	c.mu.Unlock()

	// Wait for the final response in the background
	go func() {
		resp, ok := <-respCh
		if !ok {
			once.Do(func() { close(ch) })
			return
		}
		// If there's an error in the response, send it
		if resp != nil && resp.Error != nil {
			c.mu.Lock()
			sCh := c.streamCh
			c.streamCh = nil
			c.mu.Unlock()
			if sCh != nil {
				sCh <- sse.StreamChunk{
					Content: "Error: " + resp.Error.Message,
					Done:    true,
					Error:   resp.Error,
				}
			}
		}
		// Clean up and close the channel
		c.mu.Lock()
		if c.streamCh == ch {
			c.streamCh = nil
		}
		c.mu.Unlock()
		once.Do(func() { close(ch) })
	}()

	return ch, nil
}

// ListConversations sends a listConversations request.
// Returns (nil, nil) if the method is not supported.
func (c *Client) ListConversations(ctx context.Context, agentName string) ([]sse.Conversation, error) {
	params := map[string]string{"agent_id": agentName}
	resp, err := c.call("listConversations", params)
	if err != nil {
		// Check for Method not found
		if rpcErr, ok := err.(*RPCError); ok && rpcErr.Code == MethodNotFound {
			return nil, nil
		}
		return nil, err
	}

	var conversations []sse.Conversation
	if err := json.Unmarshal(resp.Result, &conversations); err != nil {
		return nil, err
	}
	return conversations, nil
}

// GetConversation sends a getConversation request.
// Returns (nil, nil) if the method is not supported.
func (c *Client) GetConversation(ctx context.Context, id string) (*sse.ConversationDetail, error) {
	params := map[string]string{"id": id}
	resp, err := c.call("getConversation", params)
	if err != nil {
		if rpcErr, ok := err.(*RPCError); ok && rpcErr.Code == MethodNotFound {
			return nil, nil
		}
		return nil, err
	}

	var detail sse.ConversationDetail
	if err := json.Unmarshal(resp.Result, &detail); err != nil {
		return nil, err
	}
	return &detail, nil
}

// Close shuts down the subprocess.
func (c *Client) Close() error {
	c.mu.Lock()
	c.closed = true
	c.mu.Unlock()

	// Close stdin to signal the subprocess
	if c.cmd.Process != nil {
		// Send SIGTERM
		_ = c.cmd.Process.Signal(syscall.SIGTERM)

		done := make(chan error, 1)
		go func() {
			done <- c.cmd.Wait()
		}()

		select {
		case <-done:
		case <-time.After(shutdownTimeout):
			_ = c.cmd.Process.Kill()
			<-done
		}
	}

	return nil
}
