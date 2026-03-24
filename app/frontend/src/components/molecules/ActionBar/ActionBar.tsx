import { Button } from "@/components/atoms";
import { StatusBadge } from "@/components/molecules/StatusBadge";

interface ActionBarProps {
  status: string;
  onPush?: () => void;
}

function ActionBar({ status, onPush }: ActionBarProps) {
  return (
    <div className="flex items-center justify-between px-6 py-3 bg-[var(--bg-surface)] border-t border-[var(--border)]">
      <div className="flex items-center gap-2">
        <StatusBadge status={status} />
        <span className="text-xs text-[var(--fg-muted)]">
          {status === "created" ? "Not yet pushed" : `Status: ${status}`}
        </span>
      </div>
      <Button
        variant="primary"
        size="sm"
        onClick={onPush}
        disabled={!onPush}
      >
        Mark ready &amp; push
      </Button>
    </div>
  );
}

ActionBar.displayName = "ActionBar";

export { ActionBar };
export type { ActionBarProps };
