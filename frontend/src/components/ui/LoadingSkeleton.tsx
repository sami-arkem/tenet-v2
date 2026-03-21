import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "bg-neutral-100 rounded animate-pulse",
        className,
      )}
    />
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="border border-neutral-200 rounded-base overflow-hidden">
      <div className="bg-neutral-50 border-b border-neutral-200 px-4 py-2.5">
        <Skeleton className="h-3 w-48" />
      </div>
      <div className="bg-white divide-y divide-neutral-100">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="px-4 py-3 flex items-center gap-4">
            <Skeleton className="h-3 w-32 flex-none" />
            <Skeleton className="h-3 flex-1" />
            <Skeleton className="h-5 w-16 rounded flex-none" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      <TableSkeleton rows={6} />
    </div>
  );
}
