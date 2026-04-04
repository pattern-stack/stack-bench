import { useCallback, useEffect, useRef, useState } from "react";
import {
  SSE_EVENT_MAP,
  type SSEEventName,
  type StreamChunk,
  type StreamChunkType,
} from "../types/chat";

interface UseEventSourceOptions {
  channel: string;
  enabled?: boolean;
}

interface UseEventSourceReturn {
  chunks: StreamChunk[];
  isConnected: boolean;
  error: string | null;
  reconnect: () => void;
  clearChunks: () => void;
}

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;

export function useEventSource({
  channel,
  enabled = true,
}: UseEventSourceOptions): UseEventSourceReturn {
  const [chunks, setChunks] = useState<StreamChunk[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cleanup = useCallback(() => {
    if (retryTimeoutRef.current !== null) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!channel || !enabled) return;

    cleanup();

    const url = `/api/v1/events/stream?channel=${encodeURIComponent(channel)}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
      retryCountRef.current = 0;
    };

    es.onerror = () => {
      setIsConnected(false);
      es.close();
      eventSourceRef.current = null;

      if (retryCountRef.current < MAX_RETRIES) {
        const delay = BASE_DELAY_MS * Math.pow(2, retryCountRef.current);
        retryCountRef.current += 1;
        retryTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      } else {
        setError("Connection failed after maximum retries");
      }
    };

    // Register a listener for each SSE event type in the map
    const eventNames = Object.keys(SSE_EVENT_MAP) as SSEEventName[];
    for (const eventName of eventNames) {
      const chunkType: StreamChunkType = SSE_EVENT_MAP[eventName];
      es.addEventListener(eventName, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as Omit<StreamChunk, "type">;
          const chunk: StreamChunk = { ...data, type: chunkType };
          setChunks((prev) => [...prev, chunk]);
        } catch {
          setError(`Failed to parse SSE data for event "${eventName}"`);
        }
      });
    }
  }, [channel, enabled, cleanup]);

  const reconnect = useCallback(() => {
    retryCountRef.current = 0;
    setError(null);
    connect();
  }, [connect]);

  const clearChunks = useCallback(() => {
    setChunks([]);
  }, []);

  useEffect(() => {
    if (enabled && channel) {
      connect();
    } else {
      cleanup();
      setIsConnected(false);
    }

    return cleanup;
  }, [channel, enabled, connect, cleanup]);

  return { chunks, isConnected, error, reconnect, clearChunks };
}
