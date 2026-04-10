# agentic-tui

A standalone, language-agnostic terminal chat UI for AI agents. Built with [Bubble Tea](https://github.com/charmbracelet/bubbletea) v2.

Any agent backend — in any language — can drive this TUI via HTTP/SSE, JSON-RPC stdio, or direct CLI integration. Ships with built-in support for Claude Code, Gemini CLI, and any CLI that outputs text.

## Quick Start

```go
package main

import (
    "fmt"
    "os"
    tui "github.com/dugshub/agentic-tui"
)

func main() {
    app, err := tui.New(tui.Config{
        AppName:    "My Agent",
        BackendURL: "http://localhost:8000",
    })
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
    app.Run()
}
```

## Transport Modes

### CLI Agent (built-in JSONL parsing)

Zero-config integration with Claude Code, Gemini CLI, and other agents that support streaming JSONL output.

```go
tui.New(tui.Config{
    AppName: "Claude",
    BackendCLI: &tui.CLIAgentConfig{
        Command: "claude",
        Args:    []string{"-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages", "--model", "sonnet"},
        Format:  tui.FormatClaude,
    },
})
```

### HTTP/SSE

Connect to any backend that implements the SSE event protocol.

```go
tui.New(tui.Config{
    AppName:    "My Agent",
    BackendURL: "http://localhost:8000",
})
```

### JSON-RPC Stdio

Spawn a subprocess and communicate via JSON-RPC 2.0 over stdin/stdout.

```go
tui.New(tui.Config{
    AppName: "Python Agent",
    BackendStdio: &tui.StdioConfig{
        Command: "python3",
        Args:    []string{"agent.py"},
    },
})
```

### Raw Exec

Pipe prompts to any CLI tool and render stdout as markdown.

```go
tui.New(tui.Config{
    AppName: "Aider",
    BackendExec: &tui.ExecConfig{
        Command: "aider",
        Args:    []string{"--yes", "--message"},
    },
})
```

## Features

- **Part-aware messages** — text, thinking, tool calls, and errors rendered as distinct visual blocks
- **Streaming** — real-time token-by-token rendering with animated spinners
- **Tool call display** — display types for generic, diff, code, and bash with syntax highlighting
- **Diff rendering** — structured unified diffs with chroma syntax highlighting on added lines
- **14 spinner presets** — graduated escalation (subtle < 5s, pulse 5-15s, heartbeat > 15s)
- **Theme system** — dark/light themes with auto-detect, YAML-loaded, extensible
- **Slash commands** — built-in `/help`, `/clear`, `/agents`, `/quit` + custom commands
- **Custom themes** — register your own theme via `Config.Theme`

## Demos

```bash
just demo      # Scripted conversation replay (no backend needed)
just gallery   # Component showcase
just spinners  # All 14 spinner presets
just claude    # Chat with Claude Code via Sonnet
just gemini    # Chat with Gemini CLI
just echo      # Python echo agent (no API keys)
```

## Protocol

See [PROTOCOL.md](PROTOCOL.md) for the full backend contract — SSE events, JSON-RPC methods, HTTP endpoints, and display types.

## Examples

| Example | Transport | Description |
|---------|-----------|-------------|
| [`claude-code`](_examples/claude-code/) | BackendCLI | Claude Code with streaming JSONL |
| [`gemini`](_examples/gemini/) | BackendCLI | Gemini CLI with streaming JSONL |
| [`stdio-python`](_examples/stdio-python/) | BackendStdio | Python JSON-RPC echo agent |
| [`minimal`](_examples/minimal/) | BackendURL | HTTP/SSE backend connection |
| [`custom-commands`](_examples/custom-commands/) | BackendURL | Registering custom slash commands |
| [`custom-theme`](_examples/custom-theme/) | BackendURL | Custom color theme |

## Architecture

```
github.com/dugshub/agentic-tui/
  tui.go              App, New(Config), Run()
  client.go           Transport factories
  config.go           Config, EndpointConfig, CLIAgentConfig, ExecConfig
  types.go            Public type aliases (StreamChunk, Client, etc.)
  PROTOCOL.md         Backend contract
  internal/
    types/            Single source of truth for all shared types
    chat/             Chat model + view (part-aware rendering)
    app/              Top-level Bubble Tea model
    httpclient/       HTTP/SSE transport
    stdioclient/      JSON-RPC stdio transport
    cliclient/        CLI agent transport (Claude, Gemini JSONL parsers)
    execclient/       Raw exec transport
    service/          Process lifecycle (ExecService, ServiceManager)
    command/          Slash command registry
    ui/               Component library
      components/
        atoms/        10 atoms (badge, codeblock, spinner, etc.)
        molecules/    11 molecules (diffblock, toolcallblock, etc.)
      theme/          Token-based theme engine
      markdown.go     Streaming markdown renderer
      goldmark.go     Custom goldmark terminal renderer
  contracttest/       Backend validation helpers
  _examples/          Reference integrations
```

## License

[BSL 1.1](LICENSE) — source available, free for non-commercial use. Converts to Apache 2.0 on 2030-04-10.
