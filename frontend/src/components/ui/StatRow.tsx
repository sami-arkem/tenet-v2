import { cn } from "@/lib/utils";

interface StatItem {
  label: string;
  value: string | number;
  variant?: "default" | "success" | "error" | "warning" | "muted";
}

interface StatRowProps {
  stats: StatItem[];
  className?: string;
}

const VARIANT_CLASSES = {
  default: "text-neutral-800",
  success: "text-success-dark",
  error: "text-danger-dark",
  warning: "text-warning-dark",
  muted: "text-neutral-400",
};

export function StatRow({ stats, className }: StatRowProps) {
  return (
    <div className={cn("flex items-center gap-6", className)}>
      {stats.map((stat, i) => (
        <div key={i} className="flex items-baseline gap-1.5">
          <span
            className={cn(
              "text-20 font-medium tabular-nums",
              VARIANT_CLASSES[stat.variant ?? "default"],
            )}
          >
            {stat.value}
          </span>
          <span className="text-12 text-neutral-400">{stat.label}</span>
        </div>
      ))}
    </div>
  );
}
