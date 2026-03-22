import { Button, Icon } from "@/components/atoms";
import { StatusBadge } from "@/components/molecules/StatusBadge";

interface ActionBarProps {
  status: string;
  onPush?: () => void;
  onRestack?: () => void;
}

function ActionBar({ status, onPush, onRestack }: ActionBarProps) {
  return (
    <div className="flex items-center justify-between px-6 py-3 bg-[var(--bg-surface)] border-t border-[var(--border)]">
      <div className="flex items-center gap-3">
        <StatusBadge status={status} />
        <span className="text-xs text-[var(--fg-muted)]">
          {status === "created" ? "Not yet pushed" : `Status: ${status}`}
        </span>
        <Button
          variant="subtle"
          size="sm"
          onClick={onRestack}
          disabled={!onRestack}
        >
          <Icon name="refresh-cw" size="xs" />
          Restack downstream
        </Button>
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
