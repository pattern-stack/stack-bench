import { Icon } from "@/components/atoms/Icon";
import { getIcon, getFileColor } from "@/lib/file-icons";
import { cn } from "@/lib/utils";

interface FileIconProps {
  type: "file" | "dir";
  isOpen?: boolean;
  fileName?: string;
  className?: string;
}

function FileIcon({ type, isOpen = false, fileName, className }: FileIconProps) {
  if (type === "dir") {
    const entry = fileName ? getIcon(fileName, "dir", isOpen) : getIcon("", "dir", isOpen);
    return (
      <span className={cn("inline-flex items-center", className)}>
        <Icon
          name={isOpen ? "chevron-down" : "chevron-right"}
          size="xs"
          className="text-[var(--fg-subtle)] mr-0.5"
        />
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width={16}
          height={16}
          viewBox={entry.viewBox ?? "0 0 24 24"}
          fill="none"
          stroke="currentColor"
          strokeWidth={0}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="inline-block shrink-0"
          style={{ color: entry.color }}
          dangerouslySetInnerHTML={{ __html: entry.svg }}
        />
      </span>
    );
  }

  const entry = fileName ? getIcon(fileName, "file") : getIcon("", "file");

  return (
    <span className={cn("inline-flex items-center", className)}>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width={16}
        height={16}
        viewBox={entry.viewBox ?? "0 0 24 24"}
        fill="none"
        stroke="currentColor"
        strokeWidth={0}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="inline-block shrink-0 ml-[14px]"
        style={{ color: entry.color }}
        dangerouslySetInnerHTML={{ __html: entry.svg }}
      />
    </span>
  );
}

FileIcon.displayName = "FileIcon";

export { FileIcon, getFileColor };
export type { FileIconProps };
