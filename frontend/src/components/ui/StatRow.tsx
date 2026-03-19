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
  default: "text-text",
  success: "text-emerald-700",
  error: "text-red-700",
  warning: "text-amber-700",
  muted: "text-text-muted",
};

export function StatRow({ stats, className }: StatRowProps) {
  return (
    <div className={cn("flex items-center gap-6", className)}>
      {stats.map((stat, i) => (
        <div key={i} className="flex items-baseline gap-1.5">
          <span
            className={cn(
              "text-xl font-semibold tabular-nums",
              VARIANT_CLASSES[stat.variant ?? "default"],
            )}
          >
            {stat.value}
          </span>
          <span className="text-xs text-text-muted">{stat.label}</span>
        </div>
      ))}
    </div>
  );
}
