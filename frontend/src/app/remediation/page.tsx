"use client";

import useSWR from "swr";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { getRemediationDashboard } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { DataTable } from "@/components/ui/DataTable";
import { PageSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatRow } from "@/components/ui/StatRow";
import { BlockingBanner } from "@/components/ui/BlockingBanner";
import { formatDateOnly } from "@/lib/utils";
import type { RemediationItem } from "@/lib/types";
import { CheckSquare, AlertTriangle, Clock } from "lucide-react";

function RemediationTable({
  rows,
  onRowClick,
  emptyMessage,
}: {
  rows: RemediationItem[];
  onRowClick: (row: RemediationItem) => void;
  emptyMessage?: string;
}) {
  return (
    <DataTable<RemediationItem>
      columns={[
        {
          key: "title",
          header: "Title",
          render: (row) => (
            <div>
              <div className="font-medium text-text">{row.title}</div>
              <div className="text-xs text-text-secondary mt-0.5 leading-relaxed line-clamp-2">
                {row.gap_note}
              </div>
            </div>
          ),
        },
        {
          key: "severity",
          header: "Severity",
          width: "90px",
          render: (row) => {
            const s = row.severity?.toUpperCase();
            const cls =
              s === "CRITICAL"
                ? "text-red-700 bg-red-50 border-red-200"
                : s === "HIGH"
                  ? "text-orange-700 bg-orange-50 border-orange-200"
                  : s === "MEDIUM"
                    ? "text-amber-700 bg-amber-50 border-amber-200"
                    : "text-gray-600 bg-gray-50 border-gray-200";
            return (
              <span
                className={`inline-flex items-center border font-medium rounded uppercase tracking-wide px-2 py-0.5 text-[11px] ${cls}`}
              >
                {row.severity ?? "—"}
              </span>
            );
          },
        },
        {
          key: "status",
          header: "Status",
          width: "130px",
          render: (row) => <StatusBadge status={row.status} />,
        },
        {
          key: "owner",
          header: "Owner",
          width: "120px",
          render: (row) => (
            <span className="text-xs text-text-secondary mono">
              {row.owner_user_id ?? "Unassigned"}
            </span>
          ),
        },
        {
          key: "due_date",
          header: "Due",
          width: "100px",
          render: (row) =>
            row.due_date ? (
              <span className="text-xs text-text-secondary">
                {formatDateOnly(row.due_date)}
              </span>
            ) : (
              <span className="text-xs text-text-muted">—</span>
            ),
        },
        {
          key: "release_blocking",
          header: "Blocking",
          width: "80px",
          render: (row) =>
            row.release_blocking ? (
              <span className="text-[10px] text-red-700 bg-red-50 border border-red-200 rounded px-1.5 py-0.5 font-medium uppercase tracking-wide">
                Yes
              </span>
            ) : (
              <span className="text-xs text-text-muted">—</span>
            ),
        },
      ]}
      rows={rows}
      getKey={(row) => row.remediation_id}
      onRowClick={onRowClick}
      emptyMessage={emptyMessage}
    />
  );
}

export default function RemediationPage() {
  const { userId } = useAuth();
  const router = useRouter();

  const {
    data: dashboard,
    error,
    isLoading,
    mutate,
  } = useSWR(
    userId ? ["remediation-dashboard", userId] : null,
    ([, uid]) => getRemediationDashboard(uid),
    { refreshInterval: 15_000 },
  );

  function goToDetail(row: RemediationItem) {
    router.push(`/remediation/${row.remediation_id}`);
  }

  if (isLoading) return <PageSkeleton />;
  if (error)
    return (
      <ErrorMessage
        message={error.message ?? "Failed to load dashboard."}
        onRetry={() => mutate()}
      />
    );

  if (!dashboard) return null;

  const hasOverdue = dashboard.overdue_count > 0;
  const hasBlocking = dashboard.release_blocking_count > 0;

  return (
    <>
      <PageHeader
        title="Remediation"
        subtitle={`Today: ${dashboard.today}`}
      />

      {/* Blocking banners */}
      {hasOverdue && (
        <BlockingBanner
          className="mb-4"
          title={`${dashboard.overdue_count} item${dashboard.overdue_count !== 1 ? "s" : ""} overdue`}
          reasons={[]}
          variant="error"
        />
      )}
      {hasBlocking && (
        <BlockingBanner
          className="mb-6"
          title={`${dashboard.release_blocking_count} release-blocking item${dashboard.release_blocking_count !== 1 ? "s" : ""} open`}
          reasons={[]}
          variant="warning"
        />
      )}

      {/* Stats */}
      <Card className="mb-6">
        <StatRow
          stats={[
            { label: "total", value: dashboard.total_items },
            {
              label: "overdue",
              value: dashboard.overdue_count,
              variant: dashboard.overdue_count > 0 ? "error" : "muted",
            },
            {
              label: "due soon",
              value: dashboard.due_soon.length,
              variant: dashboard.due_soon.length > 0 ? "warning" : "muted",
            },
            { label: "in progress", value: dashboard.in_progress.length },
            { label: "open", value: dashboard.open.length },
            {
              label: "release-blocking",
              value: dashboard.release_blocking_count,
              variant: dashboard.release_blocking_count > 0 ? "error" : "muted",
            },
          ]}
        />
      </Card>

      {/* Overdue */}
      {dashboard.overdue.length > 0 && (
        <Card className="mb-6" padding={false}>
          <div className="px-5 py-4 border-b border-surface-border flex items-center gap-2">
            <AlertTriangle size={14} className="text-red-600" />
            <SectionHeader title="Overdue" className="mb-0" />
          </div>
          <RemediationTable
            rows={dashboard.overdue}
            onRowClick={goToDetail}
          />
        </Card>
      )}

      {/* Due Soon */}
      {dashboard.due_soon.length > 0 && (
        <Card className="mb-6" padding={false}>
          <div className="px-5 py-4 border-b border-surface-border flex items-center gap-2">
            <Clock size={14} className="text-amber-600" />
            <SectionHeader title="Due Soon (7 days)" className="mb-0" />
          </div>
          <RemediationTable
            rows={dashboard.due_soon}
            onRowClick={goToDetail}
          />
        </Card>
      )}

      {/* In Progress */}
      <Card className="mb-6" padding={false}>
        <div className="px-5 py-4 border-b border-surface-border">
          <SectionHeader title="In Progress" className="mb-0" />
        </div>
        <RemediationTable
          rows={dashboard.in_progress}
          onRowClick={goToDetail}
          emptyMessage="No items in progress."
        />
      </Card>

      {/* Open */}
      <Card className="mb-6" padding={false}>
        <div className="px-5 py-4 border-b border-surface-border">
          <SectionHeader title="Open" className="mb-0" />
        </div>
        <RemediationTable
          rows={dashboard.open}
          onRowClick={goToDetail}
          emptyMessage="No open items."
        />
      </Card>

      {/* Resolved */}
      {dashboard.resolved.length > 0 && (
        <Card padding={false}>
          <div className="px-5 py-4 border-b border-surface-border">
            <SectionHeader title="Resolved" className="mb-0" />
          </div>
          <RemediationTable
            rows={dashboard.resolved}
            onRowClick={goToDetail}
          />
        </Card>
      )}

      {dashboard.total_items === 0 && (
        <EmptyState
          icon={<CheckSquare size={22} />}
          title="No remediation items"
          description="Run an audit and sync findings to populate remediation items."
        />
      )}
    </>
  );
}
