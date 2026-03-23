import { useState, useCallback, useRef, useEffect } from "react";
import { Icon } from "@/components/atoms/Icon";

interface CommentInputProps {
  onSubmit: (body: string) => void;
  onCancel: () => void;
  lineCount?: number;
}

function CommentInput({ onSubmit, onCancel, lineCount }: CommentInputProps) {
  const [body, setBody] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = useCallback(() => {
    const trimmed = body.trim();
    if (trimmed) {
      onSubmit(trimmed);
      setBody("");
    }
  }, [body, onSubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleSubmit();
      }
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
      }
    },
    [handleSubmit, onCancel]
  );

  return (
    <div className="mx-4 my-2 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] shadow-lg shadow-black/20 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-muted)]">
        <div className="flex items-center gap-2 text-xs text-[var(--fg-muted)]">
          <div className="w-5 h-5 rounded-full bg-[var(--accent)] flex items-center justify-center">
            <span className="text-[10px] text-white font-medium">Y</span>
          </div>
          <span>
            {lineCount && lineCount > 1
              ? `Comment on ${lineCount} lines`
              : "Add a comment"}
          </span>
        </div>
        <button
          type="button"
          className="p-0.5 rounded text-[var(--fg-subtle)] hover:text-[var(--fg-muted)] transition-colors cursor-pointer"
          onClick={onCancel}
        >
          <Icon name="x" size="xs" />
        </button>
      </div>

      {/* Textarea */}
      <div className="p-2">
        <textarea
          ref={textareaRef}
          className="w-full px-2 py-1.5 text-sm bg-transparent text-[var(--fg-default)] placeholder:text-[var(--fg-subtle)] resize-none focus:outline-none"
          placeholder="Write a comment..."
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
        />
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-3 py-2 border-t border-[var(--border-muted)]">
        <span className="text-[10px] text-[var(--fg-subtle)]">
          ⌘↵ to submit · Esc to cancel
        </span>
        <button
          type="button"
          className="px-3 py-1 text-xs font-medium text-white bg-[var(--accent)] hover:brightness-110 rounded-md disabled:opacity-40 transition-all cursor-pointer"
          onClick={handleSubmit}
          disabled={!body.trim()}
        >
          Comment
        </button>
      </div>
    </div>
  );
}

CommentInput.displayName = "CommentInput";

export { CommentInput };
export type { CommentInputProps };
