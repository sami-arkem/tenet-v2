"use client";

import useSWR from "swr";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { listEvidence } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DataTable } from "@/components/ui/DataTable";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Button } from "@/components/ui/Button";
import { PageSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatRow } from "@/components/ui/StatRow";
import { formatDate } from "@/lib/utils";
import type { EvidenceSummary } from "@/lib/types";
import { FileSearch } from "lucide-react";

// Status that requires operator review
const REVIEW_STATUSES = ["FAILED", "PROCESSING"];

export default function EvidenceReviewPage() {
  const { userId } = useAuth();
  const router = useRouter();

  const {
    data: evidence,
    error,
    isLoading,
    mutate,
  } = useSWR(
    userId ? ["evidence-all", userId] : null,
    ([, uid]) => listEvidence(uid),
    { refreshInterval: 10_000 },
  );

  if (isLoading) return <PageSkeleton />;
  if (error)
    return <ErrorMessage message={error.message} onRetry={() => mutate()} />;

  const all = evidence?.rows ?? [];
  const needsReview = all.filter((e) => REVIEW_STATUSES.includes(e.status));
  const failed = all.filter((e) => e.status === "FAILED");
  const processing = all.filter((e) => e.status === "PROCESSING");
  const ready = all.filter((e) => e.status === "READY");

  return (
    <>
      <PageHeader
        title="Evidence Review"
        subtitle="Items requiring operator attention — failed processing, OCR required, or classification review."
      />

      {/* Stats */}
      <Card className="mb-6">
        <StatRow
          stats={[
            {
              label: "needs review",
              value: needsReview.length,
              variant: needsReview.length > 0 ? "warning" : "muted",
            },
            {
              label: "failed",
              value: failed.length,
              variant: failed.length > 0 ? "error" : "muted",
            },
            {
              label: "processing",
              value: processing.length,
              variant: "default",
            },
            { label: "ready", value: ready.length, variant: "success" },
            { label: "total", value: all.length, variant: "muted" },
          ]}
        />
      </Card>

      {/* Review queue */}
      <Card className="mb-6" padding={false}>
        <div className="px-5 py-4 border-b border-surface-border">
          <SectionHeader
            title="Review Queue"
            subtitle="Evidence requiring operator action before the audit can proceed."
          />
        </div>

        {needsReview.length === 0 ? (
          <EmptyState
            icon={<FileSearch size={22} />}
            title="No items in review queue"
            description="All evidence is either READY or awaiting processing. No operator action needed."
          />
        ) : (
          <DataTable<EvidenceSummary>
            columns={[
              {
                key: "filename",
                header: "Filename",
                render: (row) => (
                  <div>
                    <div className="text-text font-medium">{row.filename}</div>
                    <div className="mono text-xs text-text-muted">{row.evidence_id}</div>
                  </div>
                ),
              },
              {
                key: "audit_id",
                header: "Audit ID",
                width: "160px",
                render: (row) => (
                  <span className="mono text-xs text-text-muted">{row.audit_id}</span>
                ),
              },
              {
                key: "category",
                header: "Category",
                width: "140px",
                render: (row) => (
                  <span className="mono text-xs text-text-secondary">
                    {row.evidence_category}
                  </span>
                ),
              },
              {
                key: "status",
                header: "Status",
                width: "110px",
                render: (row) => <StatusBadge status={row.status} />,
              },
              {
                key: "updated_at",
                header: "Updated",
                width: "150px",
                render: (row) => (
                  <span className="text-xs text-text-muted">
                    {formatDate(row.updated_at)}
                  </span>
                ),
              },
              {
                key: "actions",
                header: "",
                width: "80px",
                render: (row) => (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      router.push(`/evidence-review/${row.evidence_id}`);
                    }}
                  >
                    Review
                  </Button>
                ),
              },
            ]}
            rows={needsReview}
            getKey={(row) => row.evidence_id}
            onRowClick={(row) =>
              router.push(`/evidence-review/${row.evidence_id}`)
            }
          />
        )}
      </Card>

      {/* All evidence section */}
      <Card padding={false}>
        <div className="px-5 py-4 border-b border-surface-border">
          <SectionHeader title="All Evidence" subtitle="Across all audits." />
        </div>
        <DataTable<EvidenceSummary>
          columns={[
            {
              key: "filename",
              header: "Filename",
              render: (row) => (
                <div>
                  <div className="text-text">{row.filename}</div>
                  <div className="mono text-xs text-text-muted">
                    {row.evidence_id}
                  </div>
                </div>
              ),
            },
            {
              key: "audit_id",
              header: "Audit",
              width: "160px",
              render: (row) => (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/audits/${row.audit_id}/evidence`);
                  }}
                  className="mono text-xs text-blue-600 hover:underline"
                >
                  {row.audit_id}
                </button>
              ),
            },
            {
              key: "category",
              header: "Category",
              width: "130px",
              render: (row) => (
                <span className="mono text-xs text-text-secondary">
                  {row.evidence_category}
                </span>
              ),
            },
            {
              key: "status",
              header: "Status",
              width: "110px",
              render: (row) => <StatusBadge status={row.status} />,
            },
            {
              key: "version",
              header: "Ver",
              width: "50px",
              render: (row) => (
                <span className="text-xs text-text-muted">v{row.version_number}</span>
              ),
            },
            {
              key: "updated_at",
              header: "Updated",
              width: "150px",
              render: (row) => (
                <span className="text-xs text-text-muted">
                  {formatDate(row.updated_at)}
                </span>
              ),
            },
          ]}
          rows={all}
          getKey={(row) => row.evidence_id}
          onRowClick={(row) =>
            router.push(`/evidence-review/${row.evidence_id}`)
          }
          emptyMessage="No evidence found."
        />
      </Card>
    </>
  );
}
