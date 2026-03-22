---
title: Goldmark Terminal Renderer
date: 2026-03-21
status: draft
branch: dugshub/cli-components/4-goldmark-renderer
depends_on: [2026-03-21-cli-component-system]
adrs: [ADR-001]
---

# Goldmark Terminal Renderer

## Goal

Replace the hand-rolled markdown parser in `ui/markdown.go` with goldmark (a CommonMark-compliant Go parser) plus a custom terminal renderer that routes every AST node through the atom component system. This gives us correct markdown parsing (the current regex/string-split approach mishandles nested inline formatting, multi-line list items, and many edge cases), GFM extension support (tables, strikethrough, task lists, autolinks), and automatic theme consistency since all output flows through `theme.Resolve`. The public API (`RenderMarkdown(text string, width int) string`) does not change.

## Architecture

### Rendering Pipeline

```
Raw markdown text
  |
  v
[Streaming Fixup]  -- close unclosed fences, bold markers, etc.
  |
  v
[goldmark Parser]  -- CommonMark + GFM extensions -> AST
  |
  v
[TerminalRenderer] -- walks AST, renders each node via atoms
  |                    implements goldmark renderer.NodeRenderer
  v
Styled terminal string (ANSI escape sequences)
```

### Streaming Fixup

The function is called on every new word during LLM streaming. The raw text may contain unclosed constructs that would produce a broken AST. Before passing text to goldmark, a fixup step normalizes the input:

| Construct | Detection | Fixup |
|-----------|-----------|-------|
| Fenced code block | Odd number of ` ``` ` lines | Append closing ` ``` ` |
| Bold `**` | Odd number of `**` delimiters outside code spans | Append `**` |
| Italic `*` | Odd number of unescaped `*` outside code/bold | Append `*` |
| Inline code | Odd number of `` ` `` outside fenced blocks | Append `` ` `` |
| Link `[text](url` | Open `[` with `](` but no closing `)` | Append `)` |
| Strikethrough `~~` | Odd number of `~~` delimiters | Append `~~` |

The fixup is applied to a copy of the text; the original buffer is never mutated. This is a pre-processing step, not part of the goldmark pipeline.

Implementation note: the fixup function should count delimiters in a single pass, tracking whether we are inside a fenced code block (where inline delimiters are ignored). This replaces the current `inCodeBlock` tracking in the hand-rolled parser.

## Node Mapping

Every goldmark AST node type maps to a specific rendering strategy. Block-level nodes produce newlines between them. Inline nodes produce no newlines and are concatenated.

### Block-Level Nodes

| AST Node | Renderer Output | Atom/Style Used | Width Handling |
|----------|----------------|-----------------|----------------|
| `ast.Document` | Container, joins children with `\n\n` | -- | Passes width to children |
| `ast.Heading` (level 1) | `atoms.TextBlock` | `{Category: CatAgent, Hierarchy: Primary, Emphasis: Strong}` | Wraps at width |
| `ast.Heading` (level 2) | `atoms.TextBlock` | `{Category: CatSystem, Hierarchy: Primary, Emphasis: Strong}` | Wraps at width |
| `ast.Heading` (level 3) | `atoms.TextBlock` | `{Hierarchy: Primary, Emphasis: Strong}` | Wraps at width |
| `ast.Heading` (level 4+) | `atoms.TextBlock` | `{Hierarchy: Secondary, Emphasis: Strong}` | Wraps at width |
| `ast.Paragraph` | `atoms.TextBlock` wrapping inline children | `{Hierarchy: Secondary}` | Wraps at width |
| `ast.FencedCodeBlock` | `atoms.CodeBlock` | Delegated to atom (CatTool/Secondary) | Full width minus gutter |
| `ast.CodeBlock` (indented) | `atoms.CodeBlock` | Same as fenced, no language label | Full width minus gutter |
| `ast.ThematicBreak` | `atoms.Separator` | `{Hierarchy: Tertiary}` | Full width |
| `ast.Blockquote` | Left border + dim content | Lipgloss directly: `DimColor` foreground, `│ ` gutter prefix | Width minus 2 (gutter) |
| `ast.List` | Container, joins items with `\n` | -- | Passes width minus indent to items |
| `ast.ListItem` | `atoms.Icon(IconBullet)` + content (unordered) or number + content (ordered) | Bullet: `{Category: CatAgent}` | Width minus 4 (indent + bullet + space) |
| `ast.HTMLBlock` | Rendered as plain text (strip tags) | `{Hierarchy: Tertiary}` | Wraps at width |
| GFM `ast.Table` | Basic formatted text (columns aligned with spaces) | `{Hierarchy: Secondary}` | Truncates columns to fit width |
| GFM `ast.Table` header | Same as table cell but bold | `{Hierarchy: Secondary, Emphasis: Strong}` | -- |

### Inline Nodes

| AST Node | Renderer Output | Atom/Style Used |
|----------|----------------|-----------------|
| `ast.Text` | Plain text | Inherits parent style |
| `ast.String` | Plain text | Inherits parent style |
| `ast.CodeSpan` | `atoms.InlineCode` | `{Status: Success, Hierarchy: Secondary}` |
| `ast.Emphasis` (level 1, `*`) | Lipgloss `.Italic(true)` modifier | Modifier on parent style |
| `ast.Emphasis` (level 2, `**`) | `theme.Style{Emphasis: Strong}` resolved as bold | `{Emphasis: Strong}` merged with parent |
| `ast.Link` | Lipgloss `.Underline(true)` + CatAgent color | `{Category: CatAgent, Hierarchy: Secondary}` + underline modifier |
| `ast.AutoLink` | Same as Link | Same as Link |
| `ast.Image` | Alt text in brackets, dimmed | `[alt text]` with `{Hierarchy: Tertiary}` |
| `ast.RawHTML` | Stripped, content as plain text | Inherits parent style |
| `ast.SoftLineBreak` | Single space | -- |
| `ast.HardLineBreak` | Newline character | -- |
| GFM `ast.Strikethrough` | Lipgloss `.Strikethrough(true)` modifier | Modifier on parent style |
| GFM `ast.TaskCheckBox` | `☑` (checked) or `☐` (unchecked) | `{Category: CatAgent}` for checked, `{Hierarchy: Tertiary}` for unchecked |

### Style Inheritance

Inline nodes inherit the style context of their parent block. For example, text inside a heading inherits the heading's style, but a code span inside a heading still uses the InlineCode atom's own style (atoms override inheritance). The renderer maintains a style stack:

```
Enter Heading(1)  -> push {Category: CatAgent, Hierarchy: Primary, Emphasis: Strong}
  Enter Emphasis   -> push merge(parent, {Emphasis: Strong})  // bold within heading
    Text "hello"   -> render with merged style
  Exit Emphasis    -> pop
  CodeSpan "code"  -> atoms.InlineCode (ignores parent style)
Exit Heading       -> pop
```

## File Changes

### New File: `app/cli/internal/ui/goldmark.go` (~500 lines)

Contains:

1. **`terminalRenderer` struct** -- implements `renderer.NodeRenderer`. Holds `RenderContext`, `width int`, and `io.Writer` (the output buffer). Maintains a style stack for inline inheritance.

2. **`RegisterFuncs(reg renderer.NodeRendererFuncRegisterer)`** -- registers render functions for every node kind listed in the mapping table above. This is goldmark's extension point.

3. **Per-node render functions** -- each function has signature `func (r *terminalRenderer) renderXxx(w util.BufWriter, source []byte, node ast.Node, entering bool) (ast.WalkStatus, error)`. The `entering` bool distinguishes open/close of container nodes (e.g., entering a heading pushes style, exiting pops and writes the styled text).

4. **`streamingFixup(text string) string`** -- the pre-processing function that closes unclosed constructs for streaming tolerance.

5. **Package-level goldmark instance** -- a `goldmark.Markdown` configured with GFM extension and the custom terminal renderer. Created once via `sync.Once` for performance.

### Modified File: `app/cli/internal/ui/markdown.go`

The `RenderMarkdown` function becomes a thin wrapper:

```go
func RenderMarkdown(text string, width int) string {
    if text == "" {
        return ""
    }
    fixed := streamingFixup(text)
    return renderWithGoldmark(fixed, width)
}
```

The `MarkdownRenderer` struct, `NewMarkdownRenderer`, `WriteChunk`, `Reset`, `Text`, `SetWidth`, and `Render` methods remain unchanged -- they continue to accumulate text and call `RenderMarkdown`.

All removed:
- `renderLine`, `renderInline`, `renderCodeBlock`, `indexOfOrderedPrefix` functions
- `mdH1`, `mdH2`, `mdH3`, `mdBold`, `mdItalic`, `mdCode`, `mdCodeBlock`, `mdLink`, `mdListBullet` package-level style vars

### Kept: `app/cli/internal/ui/markdown_test.go`

All existing tests must continue to pass. The tests assert on content presence and marker stripping, not on exact ANSI sequences, so they should remain green through the transition. Additional tests are added (see Testing Strategy).

### New dependency: `go.mod`

Add `github.com/yuin/goldmark` and `github.com/yuin/goldmark-extensions` (for GFM).

## Implementation Order

1. **Add goldmark dependency** -- `go get github.com/yuin/goldmark`
2. **Implement `streamingFixup`** -- the delimiter-counting fixup function. Test it in isolation.
3. **Implement `terminalRenderer` struct** with `RegisterFuncs` and the node render functions. Start with the subset covered by existing tests: headings, paragraphs, code blocks, inline code, bold, italic, lists, links.
4. **Implement `renderWithGoldmark`** -- creates the goldmark pipeline, renders to string.
5. **Rewire `RenderMarkdown`** -- thin wrapper calling fixup then goldmark. Run existing tests.
6. **Add GFM node support** -- strikethrough, task checkboxes, tables (basic text), autolinks.
7. **Add new tests** -- blockquotes, nested lists, GFM features, streaming edge cases.
8. **Remove dead code** -- old render functions, package-level style vars.

## Token Style Mapping Summary

Complete reference for the goldmark renderer's theme token usage:

| Markdown Element | theme.Style | Lipgloss Modifiers | Atom |
|---|---|---|---|
| H1 | `{Category: CatAgent, Hierarchy: Primary, Emphasis: Strong}` | -- | TextBlock |
| H2 | `{Category: CatSystem, Hierarchy: Primary, Emphasis: Strong}` | -- | TextBlock |
| H3 | `{Hierarchy: Primary, Emphasis: Strong}` | -- | TextBlock |
| H4+ | `{Hierarchy: Secondary, Emphasis: Strong}` | -- | TextBlock |
| Paragraph | `{Hierarchy: Secondary}` | -- | TextBlock |
| Bold (`**`) | `{Emphasis: Strong}` | -- | (inline, merged with parent) |
| Italic (`*`) | -- | `.Italic(true)` | (inline modifier) |
| Strikethrough (`~~`) | -- | `.Strikethrough(true)` | (inline modifier) |
| Inline code | `{Status: Success, Hierarchy: Secondary}` | -- | InlineCode |
| Fenced code block | (delegated to atom) | -- | CodeBlock |
| Indented code block | (delegated to atom, no language) | -- | CodeBlock |
| Thematic break | `{Hierarchy: Tertiary}` | -- | Separator |
| Link / autolink | `{Category: CatAgent, Hierarchy: Secondary}` | `.Underline(true)` | (inline) |
| List bullet | `{Category: CatAgent}` | -- | Icon(IconBullet) |
| Ordered list number | `{Category: CatAgent}` | -- | (plain text) |
| Task checkbox (checked) | `{Category: CatAgent}` | -- | (plain text glyph) |
| Task checkbox (unchecked) | `{Hierarchy: Tertiary}` | -- | (plain text glyph) |
| Blockquote | `{Hierarchy: Tertiary}` | -- | (lipgloss directly, gutter prefix) |
| Blockquote gutter | `{Hierarchy: Tertiary}` | -- | (lipgloss directly) |
| Table header | `{Hierarchy: Secondary, Emphasis: Strong}` | -- | (plain text) |
| Table cell | `{Hierarchy: Secondary}` | -- | (plain text) |
| Image alt text | `{Hierarchy: Tertiary}` | -- | (plain text in brackets) |

## Testing Strategy

### Existing Tests (must pass, no changes)

All tests in `markdown_test.go` assert behavioral properties (content presence, marker stripping) rather than exact output strings. They will continue to pass because goldmark produces the same semantic output.

### New Unit Tests: `streamingFixup`

Test in `markdown_test.go` alongside existing tests:

- Unclosed code fence is closed: input with odd ` ``` ` count produces valid fenced block
- Unclosed bold `**text` gets closing `**`
- Unclosed italic `*text` gets closing `*`
- Unclosed inline code `` `code `` gets closing `` ` ``
- Unclosed link `[text](url` gets closing `)`
- Already-valid input passes through unchanged
- Nested constructs: unclosed bold inside a paragraph with a closed code fence
- Code fence contents are not fixup-targeted (delimiters inside fences are ignored)

### New Unit Tests: Node Rendering

Test individual node types through `RenderMarkdown` (integration through the full pipeline):

- **Blockquote**: output contains `│` gutter character and content text
- **Nested list**: indentation increases for nested items, bullets present at each level
- **GFM strikethrough**: `~~text~~` renders with content, markers stripped
- **GFM task list**: `- [x] done` contains `☑`, `- [ ] todo` contains `☐`
- **GFM table**: header and cell content present, formatted with spacing
- **Mixed inline**: `**bold *and italic* together**` produces content without markers
- **Link**: `[text](url)` shows text, hides URL
- **Heading levels**: H1 through H4 all render with content, strip `#` markers
- **Thematic break**: `---` produces separator character (`─`)
- **Fenced code with language**: ` ```go ` renders with `go` label text present

### Streaming Edge Cases

- Partial code fence: text ending in ` `` ` (two backticks, not three) -- should not be treated as fence
- Mid-word bold: `**bol` with no closing -- fixup closes it, renders as bold
- Empty input returns empty string
- Single newline returns empty-ish output (no crash)
- Rapidly alternating code/text blocks (simulates fast streaming)

### Performance Smoke Test

Not a unit test, but a manual verification: render a 500-line markdown document and confirm it completes in under 50ms. The goldmark parser is allocation-efficient; the main concern is that our atom rendering does not introduce pathological string copying. If needed, the goldmark instance and renderer can be pooled.

## Key Design Decisions

### goldmark over alternatives

Considered: `gomarkdown/markdown`, `russross/blackfriday`, continuing hand-rolled. goldmark wins because it is CommonMark-compliant (the others are not fully), has a clean AST walker interface via `renderer.NodeRenderer`, supports extensions (GFM) as a first-class concept, and is actively maintained. blackfriday v2 is unmaintained. gomarkdown works but has a less ergonomic renderer interface.

### Fixup before parse, not error-tolerant parsing

goldmark (like all CommonMark parsers) handles malformed input by treating unclosed delimiters as literal text. This is technically correct but produces ugly output during streaming (e.g., literal `**` appears until the closing `**` arrives). The fixup step ensures the AST always represents the user's intent, even mid-stream. The alternative -- patching the AST after parsing -- was rejected because goldmark's AST is not designed for post-hoc mutation.

### Single goldmark instance with sync.Once

Creating a goldmark parser and registering extensions has non-trivial startup cost. Since `RenderMarkdown` is called on every streaming tick (potentially 10-30 times per second), we create the parser once and reuse it. The renderer state (output buffer, style stack, width) is per-call, not shared.

### Blockquote without a new atom

The blockquote rendering (left gutter + dim text) is similar to CodeBlock's gutter but with different styling. Creating a `BlockquoteAtom` was considered but deferred -- it would be the only atom used by a single caller (the markdown renderer). If blockquotes appear in other contexts later, we promote the rendering to a proper atom. For now, lipgloss is used directly within the goldmark renderer, which is acceptable since the renderer is conceptually part of the component system's infrastructure.

### Table as basic text (not a table atom)

GFM tables need a proper `Table` atom with column alignment, truncation, and responsive width distribution. That is planned for branch 6. For this branch, tables render as space-padded text columns -- functional but not pretty. The renderer is structured so that swapping in a `Table` atom later requires changing only the `renderTable` method.

## Open Questions

1. **Should the goldmark instance be configurable?** Current decision: no. We hardcode CommonMark + GFM. If we later need to support different markdown dialects (e.g., for different LLM outputs), we can add a configuration layer.

2. **Syntax highlighting for code blocks?** The `CodeBlock` atom currently applies a single style to all code text. Syntax highlighting (via `alecthomas/chroma` or similar) is a natural follow-up but out of scope for this spec. The `Language` field on `CodeBlockData` is already plumbed through to support it.

3. **Should the style stack be exposed for testing?** Current decision: no, keep it private. Test through the public `RenderMarkdown` API. If debugging style inheritance becomes painful, we can add a debug mode that annotates output with style names.
