---
id: EP-015
title: Web Chat Parity — CLI-to-Frontend Component Migration
status: planning
created: 2026-04-04
spec: .claude/specs/2026-04-04-web-chat-parity.md
---

# Web Chat Parity — CLI-to-Frontend Component Migration

## Objective

Achieve full functional parity between the Go CLI chat experience and the React web chat. Build a complete chat component system — both conversational primitives for plain discussion and code-specific primitives for tool/diff/status rendering — using the same atomic design system and naming conventions established in the CLI.

## Issues

| ID | Title | Layer | Status | Depends On |
|----|-------|-------|--------|------------|
| SB-120 | Chat Message Types | 0: Foundation | draft | — |
| SB-121 | Chat Design Tokens | 0: Foundation | draft | — |
| SB-122 | useEventSource Hook | 0: Foundation | draft | SB-120 |
| SB-123 | useChatMessages Reducer | 0: Foundation | draft | SB-120, SB-122 |
| SB-124 | ChatCodeBlock Atom | 1a: Code Atoms | draft | SB-121 |
| SB-125 | ChatSpinner Atom | 1a: Code Atoms | draft | SB-121 |
| SB-126 | ChatInlineCode Atom | 1a: Code Atoms | draft | SB-121 |
| SB-127 | ChatSeparator Atom | 1a: Code Atoms | draft | SB-121 |
| SB-140 | ChatRoleIndicator Atom | 1b: Conversational Atoms | draft | SB-121 |
| SB-141 | ChatTimestamp Atom | 1b: Conversational Atoms | draft | SB-121 |
| SB-142 | ChatPresenceIndicator Atom | 1b: Conversational Atoms | draft | SB-121 |
| SB-144 | ChatNotice Atom | 1b: Conversational Atoms | draft | SB-121 |
| SB-143 | ChatMessageGroup Molecule | 1b: Conversational Molecules | draft | SB-140, SB-141, SB-127 |
| SB-128 | ChatMarkdown Molecule | 2: Code Molecules | draft | SB-121, SB-124, SB-126 |
| SB-129 | ChatStatusBlock Molecule | 2: Code Molecules | draft | SB-125 |
| SB-130 | ChatToolCallBlock Molecule | 2: Code Molecules | draft | SB-124, SB-125 |
| SB-131 | ChatDiffBlock Molecule | 2: Code Molecules | draft | SB-121 |
| SB-132 | ChatThinkingBlock Molecule | 2: Code Molecules | draft | SB-121 |
| SB-133 | ChatErrorBlock Molecule | 2: Code Molecules | draft | SB-121 |
| SB-134 | MessagePart Dispatcher | 3: Message Rendering | draft | SB-128–133 |
| SB-135 | ChatMessageRow | 3: Message Rendering | draft | SB-134, SB-129, SB-140–142 |
| SB-136 | ChatInput | 4: Input & Commands | draft | SB-121 |
| SB-137 | SlashCommandAutocomplete | 4: Input & Commands | draft | SB-136, SB-121 |
| SB-138 | ChatRoom Organism | 5: Organism | draft | SB-123, SB-135, SB-143, SB-144, SB-136, SB-137 |
| SB-139 | AgentPanel Migration | 5: Integration | draft | SB-138 |

## Acceptance Criteria

- [ ] All 25 components implemented with tests
- [ ] AgentPanel renders real ChatRoom with live SSE streaming
- [ ] Multi-part messages render correctly (text, thinking, tool calls, errors, diffs)
- [ ] Plain conversational messages render with role indicators, timestamps, grouping
- [ ] Slash commands with autocomplete functional
- [ ] Design tokens consistent across all chat components
- [ ] `just quality` passes in frontend
