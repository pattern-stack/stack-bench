package chat

import (
	"fmt"
	"testing"

	"github.com/dugshub/agent-tui/internal/sse"
	"github.com/dugshub/agent-tui/internal/ui/components/atoms"
)

// TestRenderDemo_PartAwareConversation renders a realistic agentic conversation
// with thinking, tool calls, errors, and text. Run with `go test -v -run TestRenderDemo`
// to see the visual output.
func TestRenderDemo_PartAwareConversation(t *testing.T) {
	width := 90
	m := newTestModel()

	userMsg := TextMessage(RoleUser, "Read the main.go file and fix the error handling")

	// 1. Thinking
	m.handleResponse(resp(sse.StreamChunk{
		Content: "The user wants me to read main.go and fix error handling. Let me start by reading the file.",
		Type:    sse.ChunkThinking,
	}))
	// 2. Text
	m.handleResponse(resp(sse.StreamChunk{Content: "I'll read the file first to understand the current error handling.\n", Type: sse.ChunkText}))
	// 3. read_file
	m.handleResponse(resp(sse.StreamChunk{
		Type:        sse.ChunkToolStart,
		ToolCallID:  "tc-1",
		ToolName:    "read_file",
		DisplayType: "code",
		Arguments:   map[string]any{"path": "main.go"},
	}))
	m.handleResponse(resp(sse.StreamChunk{
		Type:       sse.ChunkToolEnd,
		ToolCallID: "tc-1",
		ToolName:   "read_file",
		Result:     "package main\n\nimport \"fmt\"\n\nfunc main() {\n\tdata, _ := os.ReadFile(\"config.json\")\n\tfmt.Println(string(data))\n}",
		DurationMs: 12,
	}))
	// 4. Text
	m.handleResponse(resp(sse.StreamChunk{Content: "Found it — the error from `os.ReadFile` is being silently discarded. Let me fix that.\n", Type: sse.ChunkText}))
	// 5. edit_file
	m.handleResponse(resp(sse.StreamChunk{
		Type:        sse.ChunkToolStart,
		ToolCallID:  "tc-2",
		ToolName:    "edit_file",
		DisplayType: "diff",
		Arguments:   map[string]any{"path": "main.go"},
	}))
	m.handleResponse(resp(sse.StreamChunk{
		Type:       sse.ChunkToolEnd,
		ToolCallID: "tc-2",
		ToolName:   "edit_file",
		Result:     "Applied edit to main.go",
		DurationMs: 45,
	}))
	// 6. bash
	m.handleResponse(resp(sse.StreamChunk{
		Type:        sse.ChunkToolStart,
		ToolCallID:  "tc-3",
		ToolName:    "bash",
		DisplayType: "bash",
		Arguments:   map[string]any{"command": "go build ./..."},
	}))
	m.handleResponse(resp(sse.StreamChunk{
		Type:       sse.ChunkToolEnd,
		ToolCallID: "tc-3",
		ToolName:   "bash",
		Result:     "",
		DurationMs: 1200,
	}))
	// 7. Final text
	m.handleResponse(resp(sse.StreamChunk{Content: "Fixed. The error from `os.ReadFile` is now properly checked.", Type: sse.ChunkText}))
	// 8. Done
	m.handleResponse(resp(sse.StreamChunk{Done: true, Type: sse.ChunkText}))

	// === Exchange 2: failing bash ===
	userMsg2 := TextMessage(RoleUser, "Now delete the config file and test it")

	m2 := newTestModel()
	m2.handleResponse(resp(sse.StreamChunk{
		Type:        sse.ChunkToolStart,
		ToolCallID:  "tc-4",
		ToolName:    "bash",
		DisplayType: "bash",
		Arguments:   map[string]any{"command": "rm config.json && go run main.go"},
	}))
	m2.handleResponse(resp(sse.StreamChunk{
		Type:       sse.ChunkToolEnd,
		ToolCallID: "tc-4",
		ToolName:   "bash",
		ToolError:  "error: open config.json: no such file or directory\nexit status 1",
		DurationMs: 350,
	}))
	m2.handleResponse(resp(sse.StreamChunk{Content: "The error handling works correctly — it reports the missing file and exits with a non-zero status.", Type: sse.ChunkText}))
	m2.handleResponse(resp(sse.StreamChunk{Done: true, Type: sse.ChunkText}))

	// Render full conversation to stdout for visual review.
	fmt.Println("\n" + repeat("═", width))
	fmt.Println("  EP-008 DEMO: Part-Aware Message Rendering")
	fmt.Println(repeat("═", width) + "\n")

	fmt.Println(renderMessage(userMsg, width, atoms.Spinner{}, "ai:"))
	fmt.Println()
	if len(m.messages) > 0 {
		fmt.Println(renderMessage(m.messages[0], width, atoms.Spinner{}, "ai:"))
	}
	fmt.Println()
	fmt.Println(renderMessage(userMsg2, width, atoms.Spinner{}, "ai:"))
	fmt.Println()
	if len(m2.messages) > 0 {
		fmt.Println(renderMessage(m2.messages[0], width, atoms.Spinner{}, "ai:"))
	}
	fmt.Println()
	fmt.Println(repeat("═", width))

	msg := m.messages[0]
	if len(msg.Parts) < 7 {
		t.Errorf("expected at least 7 parts, got %d", len(msg.Parts))
	}
}

func repeat(s string, n int) string {
	out := ""
	for i := 0; i < n; i++ {
		out += s
	}
	return out
}
