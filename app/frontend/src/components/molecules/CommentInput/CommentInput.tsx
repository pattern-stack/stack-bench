import { useState, useCallback } from "react";

interface CommentInputProps {
  onSubmit: (body: string) => void;
  onCancel: () => void;
}

function CommentInput({ onSubmit, onCancel }: CommentInputProps) {
  const [body, setBody] = useState("");

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
    <div className="flex flex-col gap-2 p-3 bg-[var(--bg-sunken)] border-y border-[var(--border)]">
      <textarea
        className="w-full px-3 py-2 text-sm bg-[var(--bg-surface)] border border-[var(--border)] rounded text-[var(--fg)] placeholder:text-[var(--fg-muted)] resize-y min-h-[60px] focus:outline-none focus:border-[var(--accent)]"
        placeholder="Leave a comment..."
        value={body}
        onChange={(e) => setBody(e.target.value)}
        onKeyDown={handleKeyDown}
        autoFocus
        rows={2}
      />
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          className="px-3 py-1 text-xs text-[var(--fg-muted)] hover:text-[var(--fg)] rounded transition-colors cursor-pointer"
          onClick={onCancel}
        >
          Cancel
        </button>
        <button
          type="button"
          className="px-3 py-1 text-xs text-white bg-[var(--accent)] hover:bg-[var(--accent-hover)] rounded disabled:opacity-50 transition-colors cursor-pointer"
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
