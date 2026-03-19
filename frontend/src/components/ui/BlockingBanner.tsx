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
  if (reasons.length === 0) return null;

  const isError = variant === "error";

  return (
    <div
      role="alert"
      className={cn(
        "rounded border px-4 py-3",
        isError
          ? "bg-red-50 border-red-200 text-red-900"
          : "bg-amber-50 border-amber-200 text-amber-900",
        className,
      )}
    >
      <div className="flex items-start gap-2.5">
        {isError ? (
          <XCircle size={15} className="mt-0.5 flex-none text-red-600" />
        ) : (
          <AlertTriangle size={15} className="mt-0.5 flex-none text-amber-600" />
        )}
        <div className="min-w-0">
          {title && (
            <p className="text-sm font-medium mb-1">{title}</p>
          )}
          {reasons.length === 1 ? (
            <p className="text-sm">{reasons[0]}</p>
          ) : (
            <ul className="text-sm space-y-0.5">
              {reasons.map((r, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="mt-1.5 w-1 h-1 rounded-full flex-none bg-current opacity-60" />
                  {r}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
