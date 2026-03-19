import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
}

export function SectionHeader({
  title,
  subtitle,
  action,
  className,
}: SectionHeaderProps) {
  return (
    <div className={cn("flex items-start justify-between gap-4 mb-4", className)}>
      <div className="min-w-0">
        <h2 className="text-sm font-semibold text-text">{title}</h2>
        {subtitle && (
          <p className="mt-0.5 text-xs text-text-secondary">{subtitle}</p>
        )}
      </div>
      {action && <div className="flex-none">{action}</div>}
    </div>
  );
}
