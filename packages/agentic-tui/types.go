// Package tui provides a terminal UI for interacting with agentic backends.
package tui

import "github.com/dugshub/agentic-tui/internal/types"

// Type aliases for public API — all canonical definitions live in internal/types.

type StreamChunk = types.StreamChunk
type ChunkType = types.ChunkType
type AgentSummary = types.AgentSummary
type Conversation = types.Conversation
type ConversationDetailResponse = types.ConversationDetailResponse
type ConversationMessage = types.ConversationMessage
type MessagePart = types.MessagePart
type Client = types.Client
