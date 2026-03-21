"use client";

import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { getAudit, getLatestRun, getPreparationSummary, triggerAuditRun } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
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

  const { data: preparation } = useSWR(
    userId && auditId ? ["audit-preparation", auditId, userId] : null,
    ([, id, uid]) => getPreparationSummary(uid, id).catch(() => null),
    { refreshInterval: 10_000 },
  );

  const preparationBlockingReasons =
    preparation?.preparation_status === "READY"
      ? []
      : Array.isArray(preparation?.blocking_reasons)
        ? preparation.blocking_reasons.filter((value): value is string => typeof value === "string" && value.trim().length > 0)
        : [];

  const runBlocked =
    runLoading ||
    audit?.status === "RUNNING" ||
    !preparation ||
    preparation.preparation_status !== "READY";

  async function handleRun() {
    if (!preparation || preparation.preparation_status !== "READY") {
      setRunError(
        preparationBlockingReasons[0] ?? "Audit preparation is incomplete. Complete evidence intake before running the audit.",
      );
      return;
    }

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
            disabled={runBlocked}
          >
            <Play size={12} />
            Run Audit
          </Button>
        }
      />

      {runError && (
        <div className="mb-6 text-14 text-danger-dark bg-danger-light border border-danger-base/20 rounded-base px-3 py-2">
          {runError}
        </div>
      )}

      {preparation && preparation.preparation_status !== "READY" && (
        <div className="mb-6 rounded-base border border-warning-base/30 bg-warning-light px-4 py-3 text-14 text-warning-dark">
          <div className="font-medium mb-1">Run Audit is blocked</div>
          {preparationBlockingReasons.length > 0 ? (
            <ul className="list-disc pl-5 space-y-1">
              {preparationBlockingReasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          ) : (
            <div>Audit preparation is incomplete. Complete evidence intake before running the audit.</div>
          )}
        </div>
      )}

      {/* Status strip */}
      <Card className="mb-6">
        <div className="flex flex-wrap items-center gap-6">
          {[
            ["Status", <Badge key="status" variant={audit.status} />],
            ["Decision", <Badge key="decision" variant={audit.deployment_decision} />],
            ["Release Ready", <Badge key="release" variant={audit.release_ready ? "ready" : "blocked"} />],
            ["Report", <Badge key="report" variant={audit.report_ready ? "ready" : "blocked"} />],
            ["Export", <Badge key="export" variant={audit.export_ready ? "ready" : "blocked"} />],
            ["Finalization", <Badge key="final" variant={audit.finalization_ready ? "ready" : "blocked"} />],
          ].map(([label, badge]) => (
            <div key={String(label)}>
              <div className="text-11 text-neutral-400 uppercase tracking-wider mb-1">{label}</div>
              {badge}
            </div>
          ))}
        </div>

        {latestRun && (
          <CardSection bordered>
            <div className="flex flex-wrap gap-6 text-13 text-neutral-500">
              <span>
                <span className="text-neutral-400">Run ID </span>
                <span className="font-mono text-neutral-700">{latestRun.run_id}</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="text-neutral-400">Run Status </span>
                <Badge variant={latestRun.status} />
              </span>
              {latestRun.started_at && (
                <span>
                  <span className="text-neutral-400">Started </span>
                  {formatDate(latestRun.started_at)}
                </span>
              )}
              {latestRun.completed_at && (
                <span>
                  <span className="text-neutral-400">Completed </span>
                  {formatDate(latestRun.completed_at)}
                </span>
              )}
            </div>
          </CardSection>
        )}
      </Card>

      {/* Audit metadata */}
      <Card className="mb-6">
        <div className="grid grid-cols-2 gap-x-8 gap-y-4 text-14">
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
              <div className="text-11 text-neutral-400 uppercase tracking-wider mb-0.5">
                {label}
              </div>
              <div className={`text-neutral-800 ${mono ? "font-mono text-13" : ""}`}>
                {String(value)}
              </div>
            </div>
          ))}
          {audit.note && (
            <div className="col-span-2">
              <div className="text-11 text-neutral-400 uppercase tracking-wider mb-0.5">Note</div>
              <div className="text-neutral-800">{audit.note}</div>
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
              bg-white border border-neutral-200 rounded-base p-4
              flex items-start gap-3
              hover:bg-neutral-50 transition-colors duration-base
            "
          >
            <Icon size={16} className="text-neutral-500 mt-0.5 flex-none" />
            <div>
              <div className="text-14 font-medium text-neutral-800">{label}</div>
              <div className="text-13 text-neutral-500 mt-0.5">{description}</div>
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}
