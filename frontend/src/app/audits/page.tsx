"use client";

import useSWR from "swr";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { listAudits } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DataTable } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { PageSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";
import type { AuditSummary } from "@/lib/types";
import { LayoutList } from "lucide-react";

export default function AuditsPage() {
  const { userId } = useAuth();
  const router = useRouter();

  const { data, error, isLoading, mutate } = useSWR(
    userId ? ["audits", userId] : null,
    ([, uid]) => listAudits(uid!),
    { refreshInterval: 15_000 },
  );

  if (isLoading) return <PageSkeleton />;
  if (error)
    return (
      <ErrorMessage
        message={error.message ?? "Failed to load audits."}
        onRetry={() => mutate()}
      />
    );

  const audits = data ?? [];

  return (
    <>
      <PageHeader
        title="Audits"
        subtitle={`${audits.length} audit${audits.length !== 1 ? "s" : ""} in this workspace`}
        action={
          <Button
            variant="primary"
            size="sm"
            onClick={() => router.push("/audits/new")}
          >
            New Audit
          </Button>
        }
      />

      {audits.length === 0 ? (
        <EmptyState
          icon={<LayoutList size={24} />}
          title="No audits yet"
          description="Create an audit to begin tracking compliance for a system."
          action={
            <Button
              variant="primary"
              size="sm"
              onClick={() => router.push("/audits/new")}
            >
              Create first audit
            </Button>
          }
        />
      ) : (
        <DataTable<AuditSummary>
          columns={[
            {
              key: "system_name",
              header: "System",
              render: (row) => (
                <div>
                  <div className="font-medium text-text">{row.system_name}</div>
                  <div className="text-xs text-text-muted mono">
                    {row.audit_id}
                  </div>
                </div>
              ),
            },
            {
              key: "audit_kind",
              header: "Kind",
              width: "120px",
              render: (row) => (
                <span className="text-text-secondary">{row.audit_kind}</span>
              ),
            },
            {
              key: "framework",
              header: "Framework / Jurisdiction",
              width: "180px",
              render: (row) => (
                <span className="text-text-secondary">
                  {row.framework} · {row.jurisdiction}
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
              key: "decision",
              header: "Decision",
              width: "160px",
              render: (row) => (
                <StatusBadge status={row.deployment_decision} />
              ),
            },
            {
              key: "updated_at",
              header: "Updated",
              width: "160px",
              render: (row) => (
                <span className="text-text-muted text-xs">
                  {formatDate(row.updated_at)}
                </span>
              ),
            },
          ]}
          rows={audits}
          getKey={(row) => row.audit_id}
          onRowClick={(row) => router.push(`/audits/${row.audit_id}`)}
        />
      )}
    </>
  );
}
