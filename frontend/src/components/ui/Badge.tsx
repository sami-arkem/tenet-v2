// components/ui/Badge.tsx — Bible §1.4.3
import { cn } from "@/lib/utils";

export type BadgeVariant =
  // Verdict
  | "pass" | "partial" | "fail" | "missing_evidence" | "not_applicable"
  // Severity
  | "critical" | "high" | "medium" | "low"
  // Finding / remediation status
  | "open" | "in_progress" | "evidence_submitted" | "verifying" | "closed" | "dismissed"
  // RAG
  | "green" | "amber" | "red"
  // Audit / evidence status (operator UI)
  | "created" | "running" | "completed" | "blocked" | "failed" | "cancelled"
  | "processing" | "queued" | "uploading" | "finalizing" | "ready"
  | "ocr_required" | "review_required" | "missing"
  | "approved" | "conditionally_approved" | "unknown"
  | "default";

const badgeVariants: Record<string, string> = {
  // Verdicts
  pass:             "bg-success-light text-success-dark",
  partial:          "bg-warning-light text-warning-dark",
  fail:             "bg-danger-light text-danger-dark",
  missing_evidence: "bg-neutral-100 text-neutral-600",
  not_applicable:   "bg-info-light text-info-dark",
  // Severity
  critical:         "bg-danger-base text-white",
  high:             "bg-danger-light text-danger-dark",
  medium:           "bg-warning-light text-warning-dark",
  low:              "bg-neutral-100 text-neutral-600",
  // Finding/remediation status
  open:               "bg-neutral-100 text-neutral-700",
  in_progress:        "bg-info-light text-info-dark",
  evidence_submitted: "bg-warning-light text-warning-dark",
  verifying:          "bg-brand-50 text-brand-700",
  closed:             "bg-success-light text-success-dark",
  dismissed:          "bg-neutral-100 text-neutral-400",
  // RAG
  green: "bg-success-light text-success-dark border border-success-base",
  amber: "bg-warning-light text-warning-dark border border-warning-base",
  red:   "bg-danger-light text-danger-dark border border-danger-base",
  // Audit/evidence operator states
  created:               "bg-neutral-100 text-neutral-700",
  running:               "bg-info-light text-info-dark",
  completed:             "bg-success-light text-success-dark",
  blocked:               "bg-danger-light text-danger-dark",
  failed:                "bg-danger-light text-danger-dark",
  cancelled:             "bg-neutral-100 text-neutral-500",
  processing:            "bg-info-light text-info-dark",
  queued:                "bg-warning-light text-warning-dark",
  uploading:             "bg-warning-light text-warning-dark",
  finalizing:            "bg-warning-light text-warning-dark",
  ready:                 "bg-success-light text-success-dark",
  ocr_required:          "bg-warning-light text-warning-dark",
  review_required:       "bg-warning-light text-warning-dark",
  missing:               "bg-neutral-100 text-neutral-600",
  approved:              "bg-success-light text-success-dark",
  conditionally_approved:"bg-warning-light text-warning-dark",
  unknown:               "bg-neutral-100 text-neutral-500",
  // Default
  default: "bg-neutral-100 text-neutral-700",
};

const badgeLabels: Record<string, string> = {
  pass:               "PASS",
  partial:            "PARTIAL",
  fail:               "FAIL",
  missing_evidence:   "NO EVIDENCE",
  not_applicable:     "N/A",
  critical:           "CRITICAL",
  high:               "HIGH",
  medium:             "MEDIUM",
  low:                "LOW",
  open:               "OPEN",
  in_progress:        "IN PROGRESS",
  evidence_submitted: "EVIDENCE SUBMITTED",
  verifying:          "VERIFYING",
  closed:             "CLOSED",
  dismissed:          "DISMISSED",
  created:            "CREATED",
  running:            "RUNNING",
  completed:          "COMPLETED",
  blocked:            "BLOCKED",
  failed:             "FAILED",
  cancelled:          "CANCELLED",
  processing:         "PROCESSING",
  queued:             "QUEUED",
  uploading:          "UPLOADING",
  finalizing:         "FINALIZING",
  ready:              "READY",
  ocr_required:       "OCR REQUIRED",
  review_required:    "REVIEW REQUIRED",
  missing:            "MISSING",
  approved:           "APPROVED",
  conditionally_approved: "CONDITIONAL",
  unknown:            "UNKNOWN",
};

interface BadgeProps {
  variant: BadgeVariant | string;
  label?: string;
  className?: string;
}

export function Badge({ variant, label, className }: BadgeProps) {
  const key = variant.toLowerCase().replace(/ /g, "_");
  const classes = badgeVariants[key] ?? badgeVariants.default;
  const displayLabel = label ?? badgeLabels[key] ?? variant.toUpperCase().replace(/_/g, " ");

  return (
    <span
      className={cn(
        "inline-flex items-center rounded",
        "px-2 py-0.5",
        "text-11 font-medium tracking-wider",
        classes,
        className,
      )}
    >
      {displayLabel}
    </span>
  );
}
