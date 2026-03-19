import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "bg-surface-muted rounded animate-pulse",
        className,
      )}
    />
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="border border-surface-border rounded overflow-hidden">
      <div className="bg-surface-subtle border-b border-surface-border px-4 py-2.5">
        <Skeleton className="h-3 w-48" />
      </div>
      <div className="bg-surface divide-y divide-surface-border">
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
