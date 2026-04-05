import { useState, useEffect, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";

interface SlashCommand {
  name: string;
  description: string;
}

interface SlashCommandAutocompleteProps {
  query: string;
  commands: SlashCommand[];
  onSelect: (command: string) => void;
  onDismiss: () => void;
  visible: boolean;
}

const DEFAULT_COMMANDS: SlashCommand[] = [
  { name: "/help", description: "Show available commands" },
  { name: "/clear", description: "Clear chat history" },
  { name: "/agents", description: "List available agents" },
];

const MAX_VISIBLE = 6;

function filterCommands(
  commands: SlashCommand[],
  query: string,
): SlashCommand[] {
  const q = query.toLowerCase();
  return commands.filter((cmd) => cmd.name.toLowerCase().includes(q));
}

function SlashCommandAutocomplete({
  query,
  commands,
  onSelect,
  onDismiss,
  visible,
}: SlashCommandAutocompleteProps) {
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  const allCommands = commands.length > 0 ? commands : DEFAULT_COMMANDS;
  const filtered = filterCommands(allCommands, query);

  // Reset highlight when query changes
  useEffect(() => {
    setHighlightedIndex(0);
  }, [query]);

  // Scroll highlighted item into view
  useEffect(() => {
    if (!listRef.current) return;
    const items = listRef.current.children;
    const item = items[highlightedIndex] as HTMLElement | undefined;
    item?.scrollIntoView({ block: "nearest" });
  }, [highlightedIndex]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!visible || filtered.length === 0) return;

      switch (e.key) {
        case "ArrowDown": {
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev < filtered.length - 1 ? prev + 1 : 0,
          );
          break;
        }
        case "ArrowUp": {
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev > 0 ? prev - 1 : filtered.length - 1,
          );
          break;
        }
        case "Tab":
        case "Enter": {
          e.preventDefault();
          const selected = filtered[highlightedIndex];
          if (selected) {
            onSelect(selected.name);
          }
          break;
        }
        case "Escape": {
          e.preventDefault();
          onDismiss();
          break;
        }
      }
    },
    [visible, filtered, highlightedIndex, onSelect, onDismiss],
  );

  // Register keyboard listeners when visible
  useEffect(() => {
    if (!visible) return;
    document.addEventListener("keydown", handleKeyDown, true);
    return () => {
      document.removeEventListener("keydown", handleKeyDown, true);
    };
  }, [visible, handleKeyDown]);

  if (!visible || filtered.length === 0) return null;

  return (
    <div
      className={cn(
        "absolute bottom-full left-0 right-0 mb-1 z-50",
        "rounded-md border border-[var(--chat-border)]",
        "bg-[var(--chat-bg-message)]",
        "shadow-lg",
      )}
    >
      <div
        ref={listRef}
        role="listbox"
        className="overflow-y-auto"
        style={{ maxHeight: `${MAX_VISIBLE * 2.5}rem` }}
      >
        {filtered.map((cmd, index) => (
          <div
            key={cmd.name}
            role="option"
            aria-selected={index === highlightedIndex}
            className={cn(
              "flex items-baseline gap-2 px-3 py-2 cursor-pointer",
              "transition-colors",
              index === highlightedIndex
                ? "bg-[var(--chat-border)]"
                : "hover:bg-[var(--chat-border)]/50",
            )}
            onMouseEnter={() => setHighlightedIndex(index)}
            onMouseDown={(e) => {
              e.preventDefault();
              onSelect(cmd.name);
            }}
          >
            <span className="text-sm font-bold text-[var(--chat-text-primary)]">
              {cmd.name}
            </span>
            <span className="text-xs text-[var(--chat-text-secondary)]">
              {cmd.description}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

SlashCommandAutocomplete.displayName = "SlashCommandAutocomplete";

export { SlashCommandAutocomplete, DEFAULT_COMMANDS };
export type { SlashCommand, SlashCommandAutocompleteProps };
