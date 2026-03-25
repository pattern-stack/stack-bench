import { Skeleton } from "@/components/atoms/Skeleton";

function MergeFlowSkeleton() {
  return (
    <div className="space-y-3 p-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center gap-2">
          <Skeleton className="w-2 h-2 rounded-full" />
          <Skeleton className="flex-1 h-4" />
          <Skeleton className="w-12 h-4" />
        </div>
      ))}
    </div>
  );
}

MergeFlowSkeleton.displayName = "MergeFlowSkeleton";

export { MergeFlowSkeleton };
