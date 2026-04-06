import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import type { ChatMessage, ChatRole } from "@/types/chat";
import { useEventSource } from "@/hooks/useEventSource";
import { useChatMessages } from "@/hooks/useChatMessages";
import { ChatInput } from "@/components/atoms/ChatInput";
import { ChatNotice } from "@/components/atoms/ChatNotice";
import { ChatMessageRow } from "@/components/molecules/ChatMessageRow";
import { ChatMessageGroup } from "@/components/molecules/ChatMessageGroup";
import {
  SlashCommandAutocomplete,
  DEFAULT_COMMANDS,
} from "@/components/molecules/SlashCommandAutocomplete";
import type { SlashCommand } from "@/components/molecules/SlashCommandAutocomplete";

// --- Types ---

interface ChatRoomProps {
  channel: string;
  agentName?: string;
  onSendMessage?: (text: string) => void;
  initialMessages?: ChatMessage[];
}

interface MessageGroup {
  role: ChatRole;
  agentName?: string;
  timestamp: string;
  messages: ChatMessage[];
  showDateSeparator: boolean;
  dateSeparatorLabel?: string;
}

// --- Helpers ---

function isSameDay(a: string, b: string): boolean {
  return a.slice(0, 10) === b.slice(0, 10);
}

function formatDateLabel(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";

  return date.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

function groupMessages(
  messages: ChatMessage[],
  agentName?: string,
): MessageGroup[] {
  const groups: MessageGroup[] = [];
  let prevTimestamp: string | null = null;

  for (const msg of messages) {
    const currentGroup = groups[groups.length - 1];
    const needsDateSeparator =
      prevTimestamp !== null && !isSameDay(prevTimestamp, msg.timestamp);

    if (currentGroup && currentGroup.role === msg.role && !needsDateSeparator) {
      currentGroup.messages.push(msg);
    } else {
      groups.push({
        role: msg.role,
        agentName: msg.role === "assistant" ? agentName : undefined,
        timestamp: msg.timestamp,
        messages: [msg],
        showDateSeparator: needsDateSeparator,
        dateSeparatorLabel: needsDateSeparator
          ? formatDateLabel(msg.timestamp)
          : undefined,
      });
    }

    prevTimestamp = msg.timestamp;
  }

  return groups;
}

// --- Default slash commands ---

const SLASH_COMMANDS: SlashCommand[] = DEFAULT_COMMANDS;

// --- Component ---

function ChatRoom({
  channel,
  agentName,
  onSendMessage,
  initialMessages,
}: ChatRoomProps) {
  // SSE + message state
  const { chunks, isConnected, error } = useEventSource({
    channel,
    enabled: true,
  });
  const { messages, addUserMessage, clearMessages } = useChatMessages({
    chunks,
  });

  // Combine initial messages with streamed messages
  const allMessages = useMemo(() => {
    if (!initialMessages?.length) return messages;
    if (messages.length === 0) return initialMessages;
    return [...initialMessages, ...messages];
  }, [initialMessages, messages]);

  // Scroll management
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const userScrolledRef = useRef(false);

  const scrollToBottom = useCallback(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
    userScrolledRef.current = false;
    setIsAtBottom(true);
  }, []);

  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const threshold = 40;
    const atBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    setIsAtBottom(atBottom);
    if (!atBottom) {
      userScrolledRef.current = true;
    }
  }, []);

  // Auto-scroll on new messages (unless user scrolled up)
  useEffect(() => {
    if (!userScrolledRef.current) {
      scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [allMessages]);

  // Slash command autocomplete state
  const [slashQuery, setSlashQuery] = useState("");
  const [slashVisible, setSlashVisible] = useState(false);

  const handleSlashCommand = useCallback((text: string) => {
    if (text.startsWith("/")) {
      setSlashQuery(text);
      setSlashVisible(true);
    } else {
      setSlashVisible(false);
      setSlashQuery("");
    }
  }, []);

  const handleSlashSelect = useCallback(
    (command: string) => {
      setSlashVisible(false);
      setSlashQuery("");
      if (command === "/clear") {
        clearMessages();
      }
    },
    [clearMessages],
  );

  const handleSlashDismiss = useCallback(() => {
    setSlashVisible(false);
    setSlashQuery("");
  }, []);

  // Streaming state
  const isStreaming = useMemo(() => {
    if (!isConnected) return false;
    if (chunks.length === 0) return false;
    const lastChunk = chunks[chunks.length - 1]!;
    return lastChunk.type !== "done";
  }, [isConnected, chunks]);

  const isWaitingForFirstChunk = useMemo(() => {
    if (!isConnected) return false;
    if (allMessages.length === 0) return false;
    const lastMsg = allMessages[allMessages.length - 1];
    return (
      lastMsg.role === "assistant" &&
      lastMsg.parts.length === 0 &&
      isConnected
    );
  }, [isConnected, allMessages]);

  // Submit handler
  const handleSubmit = useCallback(
    (text: string) => {
      addUserMessage(text);
      onSendMessage?.(text);
      // Reset scroll lock so we auto-scroll to new messages
      userScrolledRef.current = false;
    },
    [addUserMessage, onSendMessage],
  );

  // Group messages for rendering
  const messageGroups = useMemo(
    () => groupMessages(allMessages, agentName),
    [allMessages, agentName],
  );

  const isEmpty = allMessages.length === 0;

  return (
    <div className="flex flex-col h-full bg-[var(--chat-bg)] text-[var(--chat-text-primary)]">
      {/* Header */}
      <div className="px-[var(--chat-gap-lg)] py-[var(--chat-gap-md)] border-b border-[var(--chat-border)] shrink-0">
        <span className="text-[length:var(--chat-font-base)] font-semibold text-[var(--chat-text-primary)]">
          {agentName ?? "Chat"}
        </span>
      </div>

      {/* Message area */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-[var(--chat-gap-lg)] relative"
      >
        {isEmpty ? (
          <div className="flex items-center justify-center h-full text-[var(--chat-text-tertiary)] text-[length:var(--chat-font-base)] italic">
            Start a conversation
          </div>
        ) : (
          <div className="flex flex-col gap-[var(--chat-gap-lg)]">
            {messageGroups.map((group, groupIndex) => (
              <ChatMessageGroup
                key={`group-${groupIndex}-${group.timestamp}`}
                role={group.role}
                agentName={group.agentName}
                timestamp={group.timestamp}
                showDateSeparator={group.showDateSeparator}
                dateSeparatorLabel={group.dateSeparatorLabel}
              >
                {group.messages.map((msg, msgIndex) => {
                  const isLastMessage =
                    groupIndex === messageGroups.length - 1 &&
                    msgIndex === group.messages.length - 1;
                  const isLastAssistant =
                    isLastMessage && msg.role === "assistant";

                  return (
                    <ChatMessageRow
                      key={msg.id}
                      message={msg}
                      showAttribution={false}
                      agentName={
                        msg.role === "assistant" ? agentName : undefined
                      }
                      isStreaming={isLastAssistant && isStreaming}
                      isWaiting={isLastAssistant && isWaitingForFirstChunk}
                    />
                  );
                })}
              </ChatMessageGroup>
            ))}

            {/* Connection notices */}
            {error && <ChatNotice message={error} variant="error" />}
            {!isConnected && !error && (
              <ChatNotice message="Reconnecting..." variant="info" />
            )}
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={scrollAnchorRef} />

        {/* Scroll to bottom button */}
        {!isAtBottom && (
          <button
            onClick={scrollToBottom}
            className="sticky bottom-[var(--chat-gap-sm)] left-1/2 -translate-x-1/2 flex items-center justify-center w-8 h-8 rounded-full border border-[var(--chat-border)] bg-[var(--chat-bg)] text-[var(--chat-text-primary)] cursor-pointer shadow-[0_2px_8px_rgba(0,0,0,0.15)] text-base leading-none mx-auto"
            aria-label="Scroll to bottom"
          >
            ↓
          </button>
        )}
      </div>

      {/* Input area */}
      <div className="shrink-0 border-t border-[var(--chat-border)] px-[var(--chat-gap-lg)] py-[var(--chat-gap-md)] relative">
        <SlashCommandAutocomplete
          query={slashQuery}
          commands={SLASH_COMMANDS}
          onSelect={handleSlashSelect}
          onDismiss={handleSlashDismiss}
          visible={slashVisible}
        />
        <ChatInput
          onSubmit={handleSubmit}
          onSlashCommand={handleSlashCommand}
          disabled={isStreaming}
          placeholder={
            isStreaming ? "Waiting for response..." : "Send a message..."
          }
        />
      </div>
    </div>
  );
}

ChatRoom.displayName = "ChatRoom";

export { ChatRoom };
export type { ChatRoomProps };
