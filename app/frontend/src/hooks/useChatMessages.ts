import { useCallback, useEffect, useReducer, useRef } from "react";
import type {
  ChatMessage,
  ChatMessagePart,
  StreamChunk,
  ToolCallPart,
} from "../types/chat";

// --- Public interface ---

interface UseChatMessagesOptions {
  chunks: StreamChunk[];
}

interface UseChatMessagesResult {
  messages: ChatMessage[];
  addUserMessage: (text: string) => void;
  clearMessages: () => void;
}

// --- Reducer types ---

type Action =
  | { type: "APPEND_TEXT"; content: string }
  | { type: "APPEND_THINKING"; content: string }
  | {
      type: "TOOL_START";
      toolCallId: string;
      toolName: string;
      displayType: string;
      input?: string;
    }
  | {
      type: "TOOL_END";
      toolCallId: string;
      output?: string;
      error?: string;
    }
  | { type: "ERROR"; message: string }
  | { type: "DONE" }
  | { type: "ADD_USER_MESSAGE"; text: string }
  | { type: "CLEAR" };

interface State {
  messages: ChatMessage[];
}

// --- Helpers ---

function generateId(): string {
  return crypto.randomUUID();
}

function now(): string {
  return new Date().toISOString();
}

/** Return a shallow clone of the messages array with the last assistant message replaced. */
function replaceLastAssistant(
  messages: ChatMessage[],
  updated: ChatMessage,
): ChatMessage[] {
  const result = [...messages];
  for (let i = result.length - 1; i >= 0; i--) {
    if (result[i].role === "assistant") {
      result[i] = updated;
      return result;
    }
  }
  // Should not happen — caller ensures an assistant message exists.
  return result;
}

/**
 * Find the last assistant message, or create one if none exists.
 * Returns [assistantMessage, messagesWithAssistant].
 */
function ensureAssistantMessage(
  messages: ChatMessage[],
): [ChatMessage, ChatMessage[]] {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === "assistant") {
      return [messages[i], messages];
    }
  }
  const msg: ChatMessage = {
    id: generateId(),
    role: "assistant",
    parts: [],
    timestamp: now(),
  };
  return [msg, [...messages, msg]];
}

// --- Reducer ---

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "APPEND_TEXT": {
      const [assistant, msgs] = ensureAssistantMessage(state.messages);
      const lastPart = assistant.parts[assistant.parts.length - 1];
      let newParts: ChatMessagePart[];
      if (lastPart?.type === "text") {
        newParts = [
          ...assistant.parts.slice(0, -1),
          { type: "text", content: lastPart.content + action.content },
        ];
      } else {
        newParts = [
          ...assistant.parts,
          { type: "text", content: action.content },
        ];
      }
      return {
        messages: replaceLastAssistant(msgs, {
          ...assistant,
          parts: newParts,
        }),
      };
    }

    case "APPEND_THINKING": {
      const [assistant, msgs] = ensureAssistantMessage(state.messages);
      const lastPart = assistant.parts[assistant.parts.length - 1];
      let newParts: ChatMessagePart[];
      if (lastPart?.type === "thinking") {
        newParts = [
          ...assistant.parts.slice(0, -1),
          { type: "thinking", content: lastPart.content + action.content },
        ];
      } else {
        newParts = [
          ...assistant.parts,
          { type: "thinking", content: action.content },
        ];
      }
      return {
        messages: replaceLastAssistant(msgs, {
          ...assistant,
          parts: newParts,
        }),
      };
    }

    case "TOOL_START": {
      const [assistant, msgs] = ensureAssistantMessage(state.messages);
      const toolPart: ToolCallPart = {
        type: "toolCall",
        toolCallId: action.toolCallId,
        toolName: action.toolName,
        state: "running",
        displayType:
          (action.displayType as ToolCallPart["displayType"]) ?? "generic",
        input: action.input,
      };
      return {
        messages: replaceLastAssistant(msgs, {
          ...assistant,
          parts: [...assistant.parts, toolPart],
        }),
      };
    }

    case "TOOL_END": {
      const [assistant, msgs] = ensureAssistantMessage(state.messages);
      const newParts = assistant.parts.map((part) => {
        if (
          part.type === "toolCall" &&
          part.toolCallId === action.toolCallId
        ) {
          return {
            ...part,
            state: (action.error ? "failed" : "complete") as ToolCallPart["state"],
            output: action.output,
            error: action.error,
          };
        }
        return part;
      });
      return {
        messages: replaceLastAssistant(msgs, {
          ...assistant,
          parts: newParts,
        }),
      };
    }

    case "ERROR": {
      const [assistant, msgs] = ensureAssistantMessage(state.messages);
      return {
        messages: replaceLastAssistant(msgs, {
          ...assistant,
          parts: [
            ...assistant.parts,
            { type: "error", message: action.message },
          ],
        }),
      };
    }

    case "DONE": {
      // No-op on messages — useful for external state tracking.
      return state;
    }

    case "ADD_USER_MESSAGE": {
      const userMsg: ChatMessage = {
        id: generateId(),
        role: "user",
        parts: [{ type: "text", content: action.text }],
        timestamp: now(),
      };
      // Also create a placeholder assistant message for the upcoming response.
      const assistantMsg: ChatMessage = {
        id: generateId(),
        role: "assistant",
        parts: [],
        timestamp: now(),
      };
      return {
        messages: [...state.messages, userMsg, assistantMsg],
      };
    }

    case "CLEAR": {
      return { messages: [] };
    }
  }
}

// --- Map StreamChunk → Action ---

function chunkToAction(chunk: StreamChunk): Action | null {
  switch (chunk.type) {
    case "text":
      return { type: "APPEND_TEXT", content: chunk.content ?? "" };
    case "thinking":
      return { type: "APPEND_THINKING", content: chunk.content ?? "" };
    case "toolStart":
      return {
        type: "TOOL_START",
        toolCallId: chunk.toolCallId ?? generateId(),
        toolName: chunk.toolName ?? "unknown",
        displayType: chunk.displayType ?? "generic",
        input: chunk.toolInput,
      };
    case "toolEnd":
      return {
        type: "TOOL_END",
        toolCallId: chunk.toolCallId ?? "",
        output: chunk.output,
        error: chunk.toolError,
      };
    case "error":
      return { type: "ERROR", message: chunk.error ?? "Unknown error" };
    case "done":
      return { type: "DONE" };
    default:
      return null;
  }
}

// --- Hook ---

export function useChatMessages({
  chunks,
}: UseChatMessagesOptions): UseChatMessagesResult {
  const [state, dispatch] = useReducer(reducer, { messages: [] });
  const processedIndexRef = useRef(0);

  // Process new chunks as they arrive.
  useEffect(() => {
    const start = processedIndexRef.current;
    if (start >= chunks.length) return;

    for (let i = start; i < chunks.length; i++) {
      const action = chunkToAction(chunks[i]);
      if (action) {
        dispatch(action);
      }
    }
    processedIndexRef.current = chunks.length;
  }, [chunks]);

  // Reset processed index when chunks array is cleared externally.
  useEffect(() => {
    if (chunks.length === 0) {
      processedIndexRef.current = 0;
    }
  }, [chunks.length]);

  const addUserMessage = useCallback((text: string) => {
    dispatch({ type: "ADD_USER_MESSAGE", text });
  }, []);

  const clearMessages = useCallback(() => {
    dispatch({ type: "CLEAR" });
    processedIndexRef.current = 0;
  }, []);

  return {
    messages: state.messages,
    addUserMessage,
    clearMessages,
  };
}
