---
id: SB-013
title: Streaming markdown renderer (Bubble Tea component)
status: in-progress
epic: EP-002
depends_on: []
branch: dugshub/sb-cli-chat/2-wire-cli-to-backend
pr: 18
stack: sb-cli-chat
stack_index: 2
created: 2026-03-15
---

# Streaming Markdown Renderer

## Summary

Bubble Tea component for progressive streaming markdown rendering. Used by the chat view to render agent responses as they stream in.

## Scope

What's in:
- `MarkdownRenderer` struct with `WriteChunk()`, `Render()`, `Reset()`, `SetWidth()`
- `RenderMarkdown()` for one-shot rendering
- Support: headers (h1/h2/h3), bold, italic, code blocks, inline code, lists, links
- Graceful handling of unclosed code fences during streaming

What's out:
- Full CommonMark compliance
- Image rendering
- Nested blockquotes

## Implementation

```
cli/internal/ui/markdown.go
```

## Verification

- [ ] `go build ./...` passes
- [ ] `go vet ./...` passes
- [ ] Renders streaming chunks progressively
- [ ] Unclosed code fences render partial content
- [ ] Uses project lipgloss color scheme

## Notes

GH: #15
Bundled with SB-010 in PR #18.
