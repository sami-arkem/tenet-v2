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
        <h2 className="text-14 font-semibold text-neutral-800">{title}</h2>
        {subtitle && (
          <p className="mt-0.5 text-13 text-neutral-500">{subtitle}</p>
        )}
      </div>
      {action && <div className="flex-none">{action}</div>}
    </div>
  );
}
