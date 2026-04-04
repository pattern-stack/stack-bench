// Chat role for message attribution
export type ChatRole = "user" | "assistant" | "system";

// Discriminator for message part types
export type PartType = "text" | "thinking" | "toolCall" | "error";

// Display hints for tool call rendering
export type DisplayType = "diff" | "code" | "bash" | "generic";

// Lifecycle state of a tool call
export type ToolCallState = "running" | "complete" | "failed";

// --- Message parts (discriminated union on `type`) ---

export interface TextPart {
  type: "text";
  content: string;
}

export interface ThinkingPart {
  type: "thinking";
  content: string;
}

export interface ToolCallPart {
  type: "toolCall";
  toolCallId: string;
  toolName: string;
  state: ToolCallState;
  displayType: DisplayType;
  input?: string;
  output?: string;
  error?: string;
}

export interface ErrorPart {
  type: "error";
  message: string;
}

export type ChatMessagePart = TextPart | ThinkingPart | ToolCallPart | ErrorPart;

// --- Chat message ---

export interface ChatMessage {
  id: string;
  role: ChatRole;
  parts: ChatMessagePart[];
  timestamp: string; // ISO 8601
}

// --- SSE stream chunk types ---

export type StreamChunkType =
  | "text"
  | "thinking"
  | "toolStart"
  | "toolEnd"
  | "error"
  | "done";

export interface StreamChunk {
  type: StreamChunkType;
  content?: string;
  done?: boolean;
  error?: string;
  toolCallId?: string;
  toolName?: string;
  displayType?: DisplayType;
  toolInput?: string;
  toolError?: string;
  output?: string;
}

// --- SSE event name mapping ---

/**
 * Maps backend SSE event names to internal StreamChunkType values.
 * Backends may emit either form (e.g. 'agent.tool.start' or 'tool_start').
 */
export const SSE_EVENT_MAP: Record<string, StreamChunkType> = {
  "agent.message.chunk": "text",
  "agent.message.complete": "done",
  "agent.reasoning": "thinking",
  thinking: "thinking",
  "agent.tool.start": "toolStart",
  tool_start: "toolStart",
  "agent.tool.end": "toolEnd",
  tool_end: "toolEnd",
  done: "done",
  "agent.error": "error",
  error: "error",
} as const;

/** All recognized SSE event names emitted by the backend. */
export type SSEEventName = keyof typeof SSE_EVENT_MAP;
