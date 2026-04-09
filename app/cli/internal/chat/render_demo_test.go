package chat

import (
	"fmt"
	"testing"

	"github.com/dugshub/stack-bench/app/cli/internal/api"
)

// TestRenderDemo_PartAwareConversation renders a realistic agentic conversation
// with thinking, tool calls, errors, and text — demonstrating the EP-008 part-aware model.
func TestRenderDemo_PartAwareConversation(t *testing.T) {
	width := 90
	m := newTestModel()

	// === Exchange 1: User asks to fix error handling ===
	userMsg := TextMessage(RoleUser, "Read the main.go file and fix the error handling")

	// Simulate the full stream sequence
	// 1. Thinking
	m.handleResponse(resp(api.StreamChunk{
		Content: "The user wants me to read main.go and fix error handling. Let me start by reading the file.",
		Type:    api.ChunkThinking,
	}))
	// 2. Text
	m.handleResponse(resp(api.StreamChunk{Content: "I'll read the file first to understand the current error handling.\n", Type: api.ChunkText}))
	// 3. Tool call: read_file
	m.handleResponse(resp(api.StreamChunk{
		Type:        api.ChunkToolStart,
		ToolCallID:  "tc-1",
		ToolName:    "read_file",
		DisplayType: "code",
		Arguments:   map[string]any{"path": "main.go"},
	}))
	m.handleResponse(resp(api.StreamChunk{
		Type:       api.ChunkToolEnd,
		ToolCallID: "tc-1",
		ToolName:   "read_file",
		Result:     "package main\n\nimport \"fmt\"\n\nfunc main() {\n\tdata, _ := os.ReadFile(\"config.json\")\n\tfmt.Println(string(data))\n}",
		DurationMs: 12,
	}))
	// 4. Text
	m.handleResponse(resp(api.StreamChunk{Content: "Found it — the error from `os.ReadFile` is being silently discarded. Let me fix that.\n", Type: api.ChunkText}))
	// 5. Tool call: edit_file
	m.handleResponse(resp(api.StreamChunk{
		Type:        api.ChunkToolStart,
		ToolCallID:  "tc-2",
		ToolName:    "edit_file",
		DisplayType: "diff",
		Arguments:   map[string]any{"path": "main.go"},
	}))
	m.handleResponse(resp(api.StreamChunk{
		Type:       api.ChunkToolEnd,
		ToolCallID: "tc-2",
		ToolName:   "edit_file",
		Result:     "Applied edit to main.go",
		DurationMs: 45,
	}))
	// 6. Tool call: bash (build check)
	m.handleResponse(resp(api.StreamChunk{
		Type:        api.ChunkToolStart,
		ToolCallID:  "tc-3",
		ToolName:    "bash",
		DisplayType: "bash",
		Arguments:   map[string]any{"command": "go build ./..."},
	}))
	m.handleResponse(resp(api.StreamChunk{
		Type:       api.ChunkToolEnd,
		ToolCallID: "tc-3",
		ToolName:   "bash",
		Result:     "",
		DurationMs: 1200,
	}))
	// 7. Final text
	m.handleResponse(resp(api.StreamChunk{Content: "Fixed. The error from `os.ReadFile` is now properly checked.", Type: api.ChunkText}))
	// 8. Done
	m.handleResponse(resp(api.StreamChunk{Done: true, Type: api.ChunkText}))

	// === Exchange 2: User tests error path ===
	userMsg2 := TextMessage(RoleUser, "Now delete the config file and test it")

	// Simulate second assistant response
	m2 := newTestModel()
	m2.handleResponse(resp(api.StreamChunk{
		Type:        api.ChunkToolStart,
		ToolCallID:  "tc-4",
		ToolName:    "bash",
		DisplayType: "bash",
		Arguments:   map[string]any{"command": "rm config.json && go run main.go"},
	}))
	m2.handleResponse(resp(api.StreamChunk{
		Type:       api.ChunkToolEnd,
		ToolCallID: "tc-4",
		ToolName:   "bash",
		ToolError:  "error: open config.json: no such file or directory\nexit status 1",
		DurationMs: 350,
	}))
	m2.handleResponse(resp(api.StreamChunk{Content: "The error handling works correctly — it reports the missing file and exits with a non-zero status.", Type: api.ChunkText}))
	m2.handleResponse(resp(api.StreamChunk{Done: true, Type: api.ChunkText}))

	// Render full conversation
	fmt.Println("\n" + repeat("═", width))
	fmt.Println("  EP-008 DEMO: Part-Aware Message Rendering")
	fmt.Println(repeat("═", width) + "\n")

	fmt.Println(renderMessage(userMsg, width, spinnerSet{}, true))
	fmt.Println()
	if len(m.messages) > 0 {
		fmt.Println(renderMessage(m.messages[0], width, spinnerSet{}, true))
	}
	fmt.Println()
	fmt.Println(renderMessage(userMsg2, width, spinnerSet{}, true))
	fmt.Println()
	if len(m2.messages) > 0 {
		fmt.Println(renderMessage(m2.messages[0], width, spinnerSet{}, true))
	}
	fmt.Println()
	fmt.Println("═" + repeat("═", width))

	// Verify structure
	msg := m.messages[0]
	if len(msg.Parts) != 7 {
		t.Errorf("expected 7 parts (thinking, text, tool, text, tool, tool, text), got %d", len(msg.Parts))
		for i, p := range msg.Parts {
			t.Logf("  part %d: type=%s content=%q toolcall=%v", i, p.Type, truncate(p.Content, 40), p.ToolCall != nil)
		}
	}
}

func repeat(s string, n int) string {
	out := ""
	for i := 0; i < n; i++ {
		out += s
	}
	return out
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n-3] + "..."
}
