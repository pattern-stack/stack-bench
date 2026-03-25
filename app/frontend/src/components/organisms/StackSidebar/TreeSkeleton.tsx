import { Skeleton } from "@/components/atoms/Skeleton";

function TreeSkeleton() {
  return (
    <div className="flex flex-col gap-1.5 px-3 py-2">
      <Skeleton className="h-3.5 w-[70%]" />
      <Skeleton className="h-3.5 w-[55%] ml-4" />
      <Skeleton className="h-3.5 w-[65%] ml-4" />
      <Skeleton className="h-3.5 w-[50%] ml-8" />
      <Skeleton className="h-3.5 w-[60%] ml-4" />
      <Skeleton className="h-3.5 w-[45%] ml-8" />
      <Skeleton className="h-3.5 w-[70%]" />
      <Skeleton className="h-3.5 w-[55%] ml-4" />
      <Skeleton className="h-3.5 w-[60%] ml-4" />
      <Skeleton className="h-3.5 w-[50%]" />
    </div>
  );
}

TreeSkeleton.displayName = "TreeSkeleton";

export { TreeSkeleton };
