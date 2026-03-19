import { cn } from "@/lib/utils";

type StatusVariant =
  | "READY"
  | "APPROVED"
  | "CONDITIONALLY_APPROVED"
  | "BLOCKED"
  | "FAILED"
  | "CANCELLED"
  | "PROCESSING"
  | "RUNNING"
  | "QUEUED"
  | "UPLOADING"
  | "FINALIZING"
  | "CREATED"
  | "COMPLETED"
  | "MISSING"
  | "OCR_REQUIRED"
  | "REVIEW_REQUIRED"
  | "UNKNOWN"
  | string;

const VARIANT_CLASSES: Record<string, string> = {
  READY: "bg-emerald-50 text-emerald-800 border-emerald-200",
  APPROVED: "bg-emerald-50 text-emerald-800 border-emerald-200",
  COMPLETED: "bg-emerald-50 text-emerald-800 border-emerald-200",
  CONDITIONALLY_APPROVED: "bg-amber-50 text-amber-800 border-amber-200",
  BLOCKED: "bg-red-50 text-red-800 border-red-200",
  FAILED: "bg-red-50 text-red-800 border-red-200",
  CANCELLED: "bg-gray-50 text-gray-600 border-gray-200",
  MISSING: "bg-gray-50 text-gray-600 border-gray-200",
  UNKNOWN: "bg-gray-50 text-gray-600 border-gray-200",
  PROCESSING: "bg-blue-50 text-blue-800 border-blue-200",
  RUNNING: "bg-blue-50 text-blue-800 border-blue-200",
  QUEUED: "bg-amber-50 text-amber-800 border-amber-200",
  UPLOADING: "bg-amber-50 text-amber-800 border-amber-200",
  FINALIZING: "bg-amber-50 text-amber-800 border-amber-200",
  CREATED: "bg-gray-50 text-gray-700 border-gray-200",
  OCR_REQUIRED: "bg-orange-50 text-orange-800 border-orange-200",
  REVIEW_REQUIRED: "bg-orange-50 text-orange-800 border-orange-200",
};

const FALLBACK = "bg-gray-50 text-gray-700 border-gray-200";

interface StatusBadgeProps {
  status: StatusVariant;
  label?: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, label, size = "md" }: StatusBadgeProps) {
  const classes = VARIANT_CLASSES[status] ?? FALLBACK;
  const display = (label ?? status).replace(/_/g, " ");

  return (
    <span
      className={cn(
        "inline-flex items-center border font-medium rounded uppercase tracking-wide",
        size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-[11px]",
        classes,
      )}
    >
      {display}
    </span>
  );
}
