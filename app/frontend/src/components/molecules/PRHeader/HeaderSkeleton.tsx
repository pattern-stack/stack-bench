import { Skeleton } from "@/components/atoms/Skeleton";

function HeaderSkeleton() {
  return (
    <div className="px-4 py-3 border-b border-[var(--border)] space-y-2">
      {/* Title bar */}
      <Skeleton className="h-5 w-[45%]" />
      {/* Branch meta bar */}
      <Skeleton className="h-3.5 w-[30%]" />
    </div>
  );
}

HeaderSkeleton.displayName = "HeaderSkeleton";

export { HeaderSkeleton };
