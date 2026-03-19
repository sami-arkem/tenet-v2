"use client";

import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { getAudit, getLatestRun, triggerAuditRun } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Card, CardSection } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { PageSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { formatDate } from "@/lib/utils";
import { useState } from "react";
import Link from "next/link";
import {
  ClipboardCheck,
  Upload,
  AlertTriangle,
  BarChart2,
  CheckSquare,
  Play,
} from "lucide-react";

const WORKFLOW_LINKS = (auditId: string) => [
  {
    href: `/audits/${auditId}/preparation`,
    icon: ClipboardCheck,
    label: "Audit Preparation",
    description: "Evidence checklist and readiness status",
  },
  {
    href: `/audits/${auditId}/evidence`,
    icon: Upload,
    label: "Evidence Intake",
    description: "Upload sessions and evidence processing",
  },
  {
    href: `/audits/${auditId}/findings`,
    icon: AlertTriangle,
    label: "Findings",
    description: "Deterministic audit findings",
  },
  {
    href: `/audits/${auditId}/reports`,
    icon: BarChart2,
    label: "Reports & Release",
    description: "Report status, export, and finalization",
  },
];

export default function AuditDetailPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { userId } = useAuth();
  const router = useRouter();
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const {
    data: audit,
    error: auditError,
    isLoading,
    mutate: mutateAudit,
  } = useSWR(
    userId && auditId ? ["audit", auditId, userId] : null,
    ([, id, uid]) => getAudit(uid, id),
    { refreshInterval: 10_000 },
  );

  const { data: latestRun } = useSWR(
    userId && auditId ? ["run", auditId, userId] : null,
    ([, id, uid]) => getLatestRun(uid, id).catch(() => null),
    { refreshInterval: 10_000 },
  );

  async function handleRun() {
    setRunLoading(true);
    setRunError(null);
    try {
      await triggerAuditRun(userId!, auditId);
      await mutateAudit();
    } catch (err: unknown) {
      setRunError(err instanceof Error ? err.message : "Failed to trigger run.");
    } finally {
      setRunLoading(false);
    }
  }

  if (isLoading) return <PageSkeleton />;
  if (auditError)
    return (
      <ErrorMessage
        message={auditError.message ?? "Failed to load audit."}
        onRetry={() => mutateAudit()}
      />
    );
  if (!audit) return null;

  return (
    <>
      <PageHeader
        title={audit.system_name}
        subtitle={`${audit.audit_kind} · ${audit.framework} · ${audit.jurisdiction}`}
        breadcrumbs={[
          { label: "Audits", href: "/audits" },
          { label: audit.system_name },
        ]}
        action={
          <Button
            variant="primary"
            size="sm"
            onClick={handleRun}
            loading={runLoading}
            disabled={audit.status === "RUNNING"}
          >
            <Play size={12} />
            Run Audit
          </Button>
        }
      />

      {runError && (
        <div className="mb-6 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {runError}
        </div>
      )}

      {/* Status strip */}
      <Card className="mb-6">
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <div className="text-xs text-text-muted uppercase tracking-wide mb-1">Status</div>
            <StatusBadge status={audit.status} />
          </div>
          <div>
            <div className="text-xs text-text-muted uppercase tracking-wide mb-1">Decision</div>
            <StatusBadge status={audit.deployment_decision} />
          </div>
          <div>
            <div className="text-xs text-text-muted uppercase tracking-wide mb-1">Release Ready</div>
            <StatusBadge status={audit.release_ready ? "READY" : "BLOCKED"} />
          </div>
          <div>
            <div className="text-xs text-text-muted uppercase tracking-wide mb-1">Report</div>
            <StatusBadge status={audit.report_ready ? "READY" : "BLOCKED"} />
          </div>
          <div>
            <div className="text-xs text-text-muted uppercase tracking-wide mb-1">Export</div>
            <StatusBadge status={audit.export_ready ? "READY" : "BLOCKED"} />
          </div>
          <div>
            <div className="text-xs text-text-muted uppercase tracking-wide mb-1">Finalization</div>
            <StatusBadge status={audit.finalization_ready ? "READY" : "BLOCKED"} />
          </div>
        </div>

        {latestRun && (
          <CardSection bordered>
            <div className="flex flex-wrap gap-6 text-xs text-text-secondary">
              <span>
                <span className="text-text-muted">Run ID </span>
                <span className="mono">{latestRun.run_id}</span>
              </span>
              <span>
                <span className="text-text-muted">Run Status </span>
                <StatusBadge status={latestRun.status} size="sm" />
              </span>
              {latestRun.started_at && (
                <span>
                  <span className="text-text-muted">Started </span>
                  {formatDate(latestRun.started_at)}
                </span>
              )}
              {latestRun.completed_at && (
                <span>
                  <span className="text-text-muted">Completed </span>
                  {formatDate(latestRun.completed_at)}
                </span>
              )}
            </div>
          </CardSection>
        )}
      </Card>

      {/* Audit metadata */}
      <Card className="mb-6">
        <div className="grid grid-cols-2 gap-x-8 gap-y-4 text-sm">
          {[
            ["Audit ID", audit.audit_id, true],
            ["Entity ID", audit.entity_id, false],
            ["Audit Kind", audit.audit_kind, false],
            ["Framework", audit.framework, false],
            ["Jurisdiction", audit.jurisdiction, false],
            ["Latest Run ID", audit.latest_run_id ?? "—", true],
            ["Created", formatDate(audit.created_at), false],
            ["Updated", formatDate(audit.updated_at), false],
          ].map(([label, value, mono]) => (
            <div key={String(label)}>
              <div className="text-xs text-text-muted uppercase tracking-wide mb-0.5">
                {label}
              </div>
              <div className={mono ? "mono text-text" : "text-text"}>
                {String(value)}
              </div>
            </div>
          ))}
          {audit.note && (
            <div className="col-span-2">
              <div className="text-xs text-text-muted uppercase tracking-wide mb-0.5">Note</div>
              <div className="text-text">{audit.note}</div>
            </div>
          )}
        </div>
      </Card>

      {/* Workflow navigation */}
      <div className="grid grid-cols-2 gap-3">
        {WORKFLOW_LINKS(auditId).map(({ href, icon: Icon, label, description }) => (
          <Link
            key={href}
            href={href}
            className="
              bg-surface border border-surface-border rounded p-4
              flex items-start gap-3
              hover:bg-surface-subtle transition-fast
            "
          >
            <Icon size={16} className="text-text-secondary mt-0.5 flex-none" />
            <div>
              <div className="text-sm font-medium text-text">{label}</div>
              <div className="text-xs text-text-muted mt-0.5">{description}</div>
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}
