import { Icon } from "@/components/atoms/Icon";
import { cn } from "@/lib/utils";

interface FileIconProps {
  type: "file" | "dir";
  isOpen?: boolean;
  className?: string;
}

function FileIcon({ type, isOpen = false, className }: FileIconProps) {
  if (type === "dir") {
    return (
      <span className={cn("inline-flex items-center", className)}>
        <Icon
          name={isOpen ? "chevron-down" : "chevron-right"}
          size="xs"
          className="text-[var(--fg-subtle)] mr-0.5"
        />
        <Icon
          name="folder"
          size="sm"
          className="text-[var(--fg-muted)]"
        />
      </span>
    );
  }

  return (
    <span className={cn("inline-flex items-center", className)}>
      <Icon
        name="file"
        size="sm"
        className="text-[var(--fg-subtle)] ml-[14px]"
      />
    </span>
  );
}

FileIcon.displayName = "FileIcon";

export { FileIcon };
export type { FileIconProps };
