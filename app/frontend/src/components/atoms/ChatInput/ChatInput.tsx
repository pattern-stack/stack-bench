import { useState, useRef, useCallback, useEffect } from "react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSubmit: (text: string) => void;
  onSlashCommand?: (command: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

const MAX_HEIGHT = 200;

function ChatInput({
  onSubmit,
  onSlashCommand,
  disabled = false,
  placeholder = "Send a message...",
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, []);

  useEffect(() => {
    resize();
  }, [value, resize]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const text = e.target.value;
      setValue(text);

      if (text.startsWith("/") && onSlashCommand) {
        onSlashCommand(text);
      }
    },
    [onSlashCommand],
  );

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setValue("");
  }, [value, onSubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <textarea
      ref={textareaRef}
      rows={1}
      value={value}
      onChange={handleChange}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      disabled={disabled}
      className={cn(
        "w-full resize-none rounded-[var(--chat-radius-lg)] px-[var(--chat-tool-px)] py-[var(--chat-input-py)]",
        "text-[length:var(--chat-font-base)] font-[family-name:var(--font-sans)]",
        "bg-[var(--chat-bg)] text-[var(--chat-text-primary)]",
        "border border-[var(--chat-border)]",
        "placeholder:text-[var(--chat-text-primary)]/50",
        "focus:outline-none focus:border-[var(--chat-user)]",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        "transition-colors",
      )}
      style={{ maxHeight: MAX_HEIGHT, overflowY: "auto" }}
    />
  );
}

ChatInput.displayName = "ChatInput";

export { ChatInput };
export type { ChatInputProps };
