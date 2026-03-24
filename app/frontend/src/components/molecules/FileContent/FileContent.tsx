import { cn } from "@/lib/utils";
import type { FileContent as FileContentType } from "@/types/file-tree";
import { useHighlightedFile } from "@/hooks/useHighlightedFile";

interface FileContentProps {
  file: FileContentType;
}

function FileContent({ file }: FileContentProps) {
  const { highlightedLines } = useHighlightedFile(file);
  const lines = file.content.split("\n");

  return (
    <div className="flex flex-col h-full">
      {/* File path breadcrumb */}
      <div className="px-4 py-2 border-b border-[var(--border)] bg-[var(--bg-surface)] text-xs font-[family-name:var(--font-mono)] text-[var(--fg-muted)]">
        {file.path}
      </div>

      {/* File content */}
      <div className="flex-1 overflow-auto">
        <table className="w-full border-collapse">
          <tbody>
            {lines.map((line, i) => (
              <tr key={i} className="leading-5 hover:bg-[var(--bg-surface-hover)]">
                <td
                  className={cn(
                    "w-[50px] shrink-0 text-right pr-2 pl-4 select-none",
                    "text-[var(--fg-subtle)] text-xs font-[family-name:var(--font-mono)]",
                    "border-r border-[var(--border-muted)]/50",
                    "align-top"
                  )}
                  aria-hidden="true"
                >
                  {i + 1}
                </td>
                <td
                  className={cn(
                    "pl-4 pr-4 whitespace-pre text-xs font-[family-name:var(--font-mono)]",
                    "text-[var(--fg-default)]"
                  )}
                >
                  {highlightedLines[i] ? (
                    <span dangerouslySetInnerHTML={{ __html: highlightedLines[i] }} />
                  ) : (
                    line
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

FileContent.displayName = "FileContent";

export { FileContent };
export type { FileContentProps };
