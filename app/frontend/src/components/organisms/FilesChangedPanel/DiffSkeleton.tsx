import { Skeleton } from "@/components/atoms/Skeleton";

function DiffFileSection() {
  return (
    <div className="mb-4">
      {/* File header bar */}
      <Skeleton className="h-8 w-full rounded-none" />
      {/* Code lines */}
      <div className="flex flex-col gap-1.5 mt-2 px-4">
        <Skeleton className="h-3.5 w-[90%]" />
        <Skeleton className="h-3.5 w-[75%]" />
        <Skeleton className="h-3.5 w-[85%]" />
        <Skeleton className="h-3.5 w-[60%]" />
        <Skeleton className="h-3.5 w-[70%]" />
      </div>
    </div>
  );
}

function DiffSkeleton() {
  return (
    <div className="p-4 space-y-6">
      <DiffFileSection />
      <DiffFileSection />
      <DiffFileSection />
    </div>
  );
}

DiffSkeleton.displayName = "DiffSkeleton";

export { DiffSkeleton };
