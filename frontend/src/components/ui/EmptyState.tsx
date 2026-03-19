import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  description,
  action,
  icon,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 px-6 text-center",
        className,
      )}
    >
      {icon && (
        <div className="mb-4 text-text-muted">{icon}</div>
      )}
      <p className="text-sm font-medium text-text-secondary">{title}</p>
      {description && (
        <p className="mt-1.5 text-sm text-text-muted max-w-sm">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
