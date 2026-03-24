import { Icon } from "@/components/atoms/Icon";
import { cn } from "@/lib/utils";

const extensionColors: Record<string, string> = {
  tsx: "var(--accent)",
  jsx: "var(--accent)",
  ts: "var(--yellow)",
  js: "var(--yellow)",
  css: "var(--purple)",
  scss: "var(--purple)",
  json: "var(--yellow)",
  md: "var(--fg-muted)",
  html: "var(--red)",
  go: "var(--accent)",
  py: "var(--yellow)",
};

function getExtensionColor(fileName?: string): string {
  if (!fileName) return "var(--fg-subtle)";
  const ext = fileName.split(".").pop()?.toLowerCase();
  if (!ext) return "var(--fg-subtle)";
  return extensionColors[ext] ?? "var(--fg-subtle)";
}

interface FileIconProps {
  type: "file" | "dir";
  isOpen?: boolean;
  fileName?: string;
  className?: string;
}

function FileIcon({ type, isOpen = false, fileName, className }: FileIconProps) {
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

  const color = getExtensionColor(fileName);

  return (
    <span className={cn("inline-flex items-center", className)}>
      <Icon
        name="file"
        size="sm"
        className="ml-[14px]"
        style={{ color }}
      />
    </span>
  );
}

FileIcon.displayName = "FileIcon";

export { FileIcon, extensionColors, getExtensionColor };
export type { FileIconProps };
