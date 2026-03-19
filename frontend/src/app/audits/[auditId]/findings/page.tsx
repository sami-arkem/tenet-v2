"use client";

import useSWR from "swr";
import { useParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { listFindings, syncFindings, getAudit } from "@/lib/api";
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
import { useState } from "react";
import type { FindingRow } from "@/lib/types";
import { AlertTriangle, RefreshCw } from "lucide-react";

const SEVERITY_ORDER: Record<string, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
};

function sortBySeverity(rows: FindingRow[]): FindingRow[] {
  return [...rows].sort(
    (a, b) =>
      (SEVERITY_ORDER[a.severity.toUpperCase()] ?? 9) -
      (SEVERITY_ORDER[b.severity.toUpperCase()] ?? 9),
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const s = severity.toUpperCase();
  const cls =
    s === "CRITICAL"
      ? "bg-red-100 text-red-800 border-red-200"
      : s === "HIGH"
        ? "bg-orange-100 text-orange-800 border-orange-200"
        : s === "MEDIUM"
          ? "bg-amber-100 text-amber-800 border-amber-200"
          : "bg-gray-100 text-gray-600 border-gray-200";

  return (
    <span
      className={`inline-flex items-center border font-medium rounded uppercase tracking-wide px-2 py-0.5 text-[11px] ${cls}`}
    >
      {severity}
    </span>
  );
}

export default function FindingsPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { userId } = useAuth();
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  const { data: audit } = useSWR(
    userId && auditId ? ["audit", auditId, userId] : null,
    ([, id, uid]) => getAudit(uid, id),
  );

  const {
    data: findings,
    error,
    isLoading,
    mutate,
  } = useSWR(
    userId && auditId ? ["findings", auditId, userId] : null,
    ([, id, uid]) => listFindings(uid, id),
    { refreshInterval: 15_000 },
  );

  async function handleSync() {
    setSyncing(true);
    setSyncError(null);
    try {
      await syncFindings(userId!, auditId);
      await mutate();
    } catch (err: unknown) {
      setSyncError(err instanceof Error ? err.message : "Sync failed.");
    } finally {
      setSyncing(false);
    }
  }

  if (isLoading) return <PageSkeleton />;
  if (error)
    return <ErrorMessage message={error.message} onRetry={() => mutate()} />;

  const rows = sortBySeverity(findings?.rows ?? []);
  const totalFindings = findings?.total_findings ?? 0;
  const criticalCount = rows.filter(
    (r) => r.severity.toUpperCase() === "CRITICAL",
  ).length;
  const highCount = rows.filter(
    (r) => r.severity.toUpperCase() === "HIGH",
  ).length;

  return (
    <>
      <PageHeader
        title="Findings"
        subtitle={audit?.system_name}
        breadcrumbs={[
          { label: "Audits", href: "/audits" },
          { label: audit?.system_name ?? auditId, href: `/audits/${auditId}` },
          { label: "Findings" },
        ]}
        action={
          <Button
            variant="secondary"
            size="sm"
            onClick={handleSync}
            loading={syncing}
          >
            <RefreshCw size={12} />
            Sync from Run
          </Button>
        }
      />

      {syncError && (
        <div className="mb-6 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {syncError}
        </div>
      )}

      {/* Stats */}
      <Card className="mb-6">
        <StatRow
          stats={[
            {
              label: "total findings",
              value: totalFindings,
              variant: totalFindings > 0 ? "error" : "muted",
            },
            {
              label: "critical",
              value: criticalCount,
              variant: criticalCount > 0 ? "error" : "muted",
            },
            {
              label: "high",
              value: highCount,
              variant: highCount > 0 ? "warning" : "muted",
            },
          ]}
        />
      </Card>

      {/* Findings table */}
      {rows.length === 0 ? (
        <EmptyState
          icon={<AlertTriangle size={22} />}
          title="No findings"
          description="Run the audit and sync findings to see deterministic audit results."
          action={
            <Button
              variant="secondary"
              size="sm"
              onClick={handleSync}
              loading={syncing}
            >
              Sync from Run
            </Button>
          }
        />
      ) : (
        <Card padding={false}>
          <div className="px-5 py-4 border-b border-surface-border">
            <SectionHeader
              title="Audit Findings"
              subtitle="Findings are deterministic. They are not generated by a model."
            />
          </div>
          <DataTable<FindingRow>
            columns={[
              {
                key: "severity",
                header: "Severity",
                width: "90px",
                render: (row) => <SeverityBadge severity={row.severity} />,
              },
              {
                key: "finding_type",
                header: "Type",
                width: "160px",
                render: (row) => (
                  <span className="mono text-xs text-text-secondary">
                    {row.finding_type}
                  </span>
                ),
              },
              {
                key: "title",
                header: "Title",
                render: (row) => (
                  <div>
                    <div className="font-medium text-text">{row.title}</div>
                    <div className="text-xs text-text-secondary mt-0.5 leading-relaxed">
                      {row.detail}
                    </div>
                  </div>
                ),
              },
              {
                key: "finding_id",
                header: "Finding ID",
                width: "160px",
                render: (row) => (
                  <span className="mono text-xs text-text-muted">
                    {row.finding_id}
                  </span>
                ),
              },
            ]}
            rows={rows}
            getKey={(row) => row.finding_id}
          />
        </Card>
      )}
    </>
  );
}
