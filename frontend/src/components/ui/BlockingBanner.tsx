import { AlertTriangle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface BlockingBannerProps {
  reasons: string[];
  title?: string;
  variant?: "error" | "warning";
  className?: string;
}

export function BlockingBanner({
  reasons,
  title,
  variant = "error",
  className,
}: BlockingBannerProps) {
  // Only hide if there's nothing to show at all
  if (!title && reasons.length === 0) return null;

  const isError = variant === "error";

  return (
    <div
      role="alert"
      className={cn(
        "rounded-base border px-4 py-3",
        isError
          ? "bg-danger-light border-danger-base/30 text-danger-dark"
          : "bg-warning-light border-warning-base/30 text-warning-dark",
        className,
      )}
    >
      <div className="flex items-start gap-2.5">
        {isError ? (
          <XCircle size={15} className="mt-0.5 flex-none text-danger-base" />
        ) : (
          <AlertTriangle size={15} className="mt-0.5 flex-none text-warning-base" />
        )}
        <div className="min-w-0">
          {title && (
            <p className="text-14 font-medium mb-1">{title}</p>
          )}
          {reasons.length === 1 ? (
            <p className="text-14">{reasons[0]}</p>
          ) : reasons.length > 1 ? (
            <ul className="text-14 space-y-0.5">
              {reasons.map((r, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="mt-1.5 w-1 h-1 rounded-full flex-none bg-current opacity-60" />
                  {r}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
    </div>
  );
}
