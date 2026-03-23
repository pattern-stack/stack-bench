import { useState, useCallback, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { Icon } from "@/components/atoms/Icon";

interface CommentPopoverProps {
  onSubmit: (body: string) => void;
  onCancel: () => void;
  anchorRef: React.RefObject<HTMLElement | null>;
  lineCount?: number;
}

function CommentPopover({ onSubmit, onCancel, anchorRef, lineCount }: CommentPopoverProps) {
  const [body, setBody] = useState("");
  const popoverRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number; width: number } | null>(null);

  // Position the popover relative to the anchor element
  useEffect(() => {
    const anchor = anchorRef.current;
    if (!anchor) return;

    const update = () => {
      const rect = anchor.getBoundingClientRect();
      setPos({
        top: rect.bottom + 4,
        left: rect.left + 20, // offset past the gutter
        width: Math.min(rect.width - 40, 480),
      });
    };

    update();
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [anchorRef]);

  // Focus textarea on mount
  useEffect(() => {
    // Small delay so portal is rendered
    const t = setTimeout(() => textareaRef.current?.focus(), 50);
    return () => clearTimeout(t);
  }, []);

  // Click outside to dismiss
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onCancel();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onCancel]);

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

  if (!pos) return null;

  return createPortal(
    <div
      ref={popoverRef}
      className="fixed z-50 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] shadow-xl shadow-black/30 overflow-hidden animate-in fade-in slide-in-from-top-1 duration-150"
      style={{
        top: pos.top,
        left: pos.left,
        width: pos.width,
      }}
    >
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
    </div>,
    document.body
  );
}

CommentPopover.displayName = "CommentPopover";

export { CommentPopover };
export type { CommentPopoverProps };
