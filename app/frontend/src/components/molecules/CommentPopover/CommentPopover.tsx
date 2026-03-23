import { useState, useCallback, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { Icon } from "@/components/atoms/Icon";
import type { ReviewComment } from "@/hooks/useReviewComments";

interface CommentPopoverProps {
  onSubmit: (body: string) => void;
  onCancel: () => void;
  anchorRef: React.RefObject<HTMLElement | null>;
  lineCount?: number;
  existingComments?: ReviewComment[];
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function CommentPopover({ onSubmit, onCancel, anchorRef, lineCount, existingComments }: CommentPopoverProps) {
  const [body, setBody] = useState("");
  const [showInput, setShowInput] = useState(!existingComments?.length);
  const popoverRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number; width: number } | null>(null);

  // Position the popover relative to the anchor element
  useEffect(() => {
    const anchor = anchorRef.current;
    if (!anchor) return;

    const update = () => {
      const rect = anchor.getBoundingClientRect();
      const popoverWidth = Math.min(rect.width - 40, 480);
      setPos({
        top: rect.bottom + 4,
        left: rect.left + 20,
        width: popoverWidth,
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

  // Focus textarea when input is shown
  useEffect(() => {
    if (showInput) {
      const t = setTimeout(() => textareaRef.current?.focus(), 50);
      return () => clearTimeout(t);
    }
  }, [showInput]);

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
      setShowInput(false);
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
        if (showInput && existingComments?.length) {
          setShowInput(false);
          setBody("");
        } else {
          onCancel();
        }
      }
    },
    [handleSubmit, onCancel, showInput, existingComments]
  );

  if (!pos) return null;

  const hasThread = existingComments && existingComments.length > 0;

  return createPortal(
    <div
      ref={popoverRef}
      className="fixed z-50 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] shadow-xl shadow-black/30 overflow-hidden"
      style={{
        top: pos.top,
        left: pos.left,
        width: pos.width,
      }}
    >
      {/* Existing thread */}
      {hasThread && (
        <div className="max-h-[240px] overflow-y-auto">
          {existingComments.map((comment, i) => (
            <div
              key={comment.id}
              className={i > 0 ? "border-t border-[var(--border-muted)]" : ""}
            >
              <div className="flex items-start gap-2.5 px-3 py-2.5">
                <div className="w-5 h-5 rounded-full bg-[var(--accent-muted)] flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-[10px] text-[var(--accent)] font-medium">
                    {comment.author.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-medium text-[var(--fg-default)]">
                      {comment.author}
                    </span>
                    <span className="text-[10px] text-[var(--fg-subtle)]">
                      {timeAgo(comment.created_at)}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--fg-muted)] leading-relaxed whitespace-pre-wrap">
                    {comment.body}
                  </p>
                </div>
                {comment.resolved && (
                  <Icon name="check" size="xs" className="text-[var(--green)] shrink-0 mt-1" />
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Reply / new comment input */}
      {showInput ? (
        <>
          <div className={hasThread ? "border-t border-[var(--border)]" : ""}>
            {/* Header — only for new comments (no thread) */}
            {!hasThread && (
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
            )}

            <div className="p-2">
              <textarea
                ref={textareaRef}
                className="w-full px-2 py-1.5 text-sm bg-transparent text-[var(--fg-default)] placeholder:text-[var(--fg-subtle)] resize-none focus:outline-none"
                placeholder={hasThread ? "Reply..." : "Write a comment..."}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={2}
              />
            </div>

            <div className="flex items-center justify-between px-3 py-2 border-t border-[var(--border-muted)]">
              <span className="text-[10px] text-[var(--fg-subtle)]">
                ⌘↵ to submit · Esc to {hasThread ? "close" : "cancel"}
              </span>
              <button
                type="button"
                className="px-3 py-1 text-xs font-medium text-white bg-[var(--accent)] hover:brightness-110 rounded-md disabled:opacity-40 transition-all cursor-pointer"
                onClick={handleSubmit}
                disabled={!body.trim()}
              >
                {hasThread ? "Reply" : "Comment"}
              </button>
            </div>
          </div>
        </>
      ) : (
        /* Reply button when thread is showing but input is collapsed */
        <div className="flex items-center justify-between px-3 py-2 border-t border-[var(--border)]">
          <button
            type="button"
            className="flex items-center gap-1.5 text-xs text-[var(--fg-muted)] hover:text-[var(--fg-default)] transition-colors cursor-pointer"
            onClick={() => setShowInput(true)}
          >
            <Icon name="message-square" size="xs" />
            Reply
          </button>
          <button
            type="button"
            className="p-0.5 rounded text-[var(--fg-subtle)] hover:text-[var(--fg-muted)] transition-colors cursor-pointer"
            onClick={onCancel}
          >
            <Icon name="x" size="xs" />
          </button>
        </div>
      )}
    </div>,
    document.body
  );
}

CommentPopover.displayName = "CommentPopover";

export { CommentPopover };
export type { CommentPopoverProps };
