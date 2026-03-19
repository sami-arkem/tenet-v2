"use client";

import useSWR from "swr";
import { useParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  getReportSummary,
  getExportManifest,
  getReleaseSummary,
  getAudit,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { BlockingBanner } from "@/components/ui/BlockingBanner";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { PageSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { formatBytes } from "@/lib/utils";
import { CheckCircle2, XCircle, FileText, Package } from "lucide-react";

function ReadinessRow({
  label,
  ready,
  status,
}: {
  label: string;
  ready: boolean;
  status?: string;
}) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-surface-border last:border-0">
      <div className="flex items-center gap-2.5">
        {ready ? (
          <CheckCircle2 size={14} className="text-emerald-600 flex-none" />
        ) : (
          <XCircle size={14} className="text-red-500 flex-none" />
        )}
        <span className="text-sm text-text">{label}</span>
      </div>
      {status && <StatusBadge status={status} size="sm" />}
    </div>
  );
}

export default function ReportsPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { userId } = useAuth();

  const { data: audit } = useSWR(
    userId && auditId ? ["audit", auditId, userId] : null,
    ([, id, uid]) => getAudit(uid, id),
  );

  const {
    data: report,
    error: reportError,
    isLoading: reportLoading,
    mutate: mutateReport,
  } = useSWR(
    userId && auditId ? ["report-summary", auditId, userId] : null,
    ([, id, uid]) => getReportSummary(uid, id).catch(() => null),
    { refreshInterval: 15_000 },
  );

  const {
    data: manifest,
    error: manifestError,
    isLoading: manifestLoading,
    mutate: mutateManifest,
  } = useSWR(
    userId && auditId ? ["export-manifest", auditId, userId] : null,
    ([, id, uid]) => getExportManifest(uid, id).catch(() => null),
    { refreshInterval: 15_000 },
  );

  const { data: release } = useSWR(
    userId && auditId ? ["release", auditId, userId] : null,
    ([, id, uid]) => getReleaseSummary(uid, id).catch(() => null),
    { refreshInterval: 15_000 },
  );

  if (reportLoading || manifestLoading) return <PageSkeleton />;

  const allBlocking = [
    ...(report?.blocking_reasons ?? []),
    ...(manifest?.blocking_reasons ?? []),
    ...(release?.blocking_reasons ?? []),
  ];
  const uniqueBlocking = [...new Set(allBlocking)];

  return (
    <>
      <PageHeader
        title="Reports & Release"
        subtitle={audit?.system_name}
        breadcrumbs={[
          { label: "Audits", href: "/audits" },
          { label: audit?.system_name ?? auditId, href: `/audits/${auditId}` },
          { label: "Reports" },
        ]}
      />

      {uniqueBlocking.length > 0 && (
        <BlockingBanner
          className="mb-6"
          title="Release is blocked"
          reasons={uniqueBlocking}
          variant="error"
        />
      )}

      {/* Report readiness */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        <Card>
          <SectionHeader title="Report Status" />
          {reportError ? (
            <ErrorMessage
              message="Failed to load report summary."
              onRetry={() => mutateReport()}
            />
          ) : report ? (
            <div>
              <ReadinessRow
                label="Report Ready"
                ready={report.report_ready}
                status={report.report_ready ? "READY" : "BLOCKED"}
              />
              <ReadinessRow
                label="Export Ready"
                ready={report.export_ready}
                status={report.export_ready ? "READY" : "BLOCKED"}
              />
              <ReadinessRow
                label="Finalization Ready"
                ready={report.finalization_ready}
                status={report.finalization_ready ? "READY" : "BLOCKED"}
              />
              <ReadinessRow
                label="Release Ready"
                ready={report.release_ready}
                status={report.release_status}
              />
              {report.remediation_gate_status && (
                <ReadinessRow
                  label="Remediation Gate"
                  ready={report.remediation_gate_status === "CLEAR"}
                  status={report.remediation_gate_status}
                />
              )}
              {report.run_id && (
                <div className="mt-4 pt-3 border-t border-surface-border">
                  <div className="text-xs text-text-muted uppercase tracking-wide mb-1">Run ID</div>
                  <div className="mono text-xs text-text-secondary">{report.run_id}</div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-text-muted">No report data available. Run the audit first.</p>
          )}
        </Card>

        <Card>
          <SectionHeader title="Release Gate" />
          {release ? (
            <div>
              <ReadinessRow
                label="Release"
                ready={release.release_ready}
                status={release.release_status}
              />
              <ReadinessRow
                label="Finalization"
                ready={release.finalization_ready}
                status={release.finalization_status}
              />
              {release.remediation_gate_status && (
                <ReadinessRow
                  label="Remediation Gate"
                  ready={release.remediation_ready ?? false}
                  status={release.remediation_gate_status}
                />
              )}
            </div>
          ) : (
            <p className="text-sm text-text-muted">No release data. Complete the audit run.</p>
          )}
        </Card>
      </div>

      {/* Export manifest */}
      <Card>
        <SectionHeader
          title="Export Package"
          subtitle="Immutable export artifact contents."
        />

        {manifestError ? (
          <ErrorMessage
            message="Failed to load export manifest."
            onRetry={() => mutateManifest()}
          />
        ) : manifest ? (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <Package size={15} className="text-text-secondary" />
              <div>
                <div className="text-sm text-text font-medium">
                  {manifest.package_status}
                </div>
                <div className="text-xs text-text-muted mono">{manifest.manifest_path}</div>
              </div>
              <StatusBadge
                status={manifest.package_ready ? "READY" : "BLOCKED"}
              />
            </div>

            {manifest.included_files.length > 0 ? (
              <div className="border border-surface-border rounded overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-surface-subtle border-b border-surface-border">
                    <tr>
                      <th className="px-3 py-2 text-left text-text-muted font-medium">File</th>
                      <th className="px-3 py-2 text-left text-text-muted font-medium w-24">Size</th>
                      <th className="px-3 py-2 text-left text-text-muted font-medium w-48">SHA-256</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border bg-surface">
                    {manifest.included_files.map((f, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 mono text-text-secondary">
                          <FileText size={12} className="inline mr-1.5 text-text-muted" />
                          {f.path}
                        </td>
                        <td className="px-3 py-2 text-text-muted">
                          {f.size != null ? formatBytes(f.size) : "—"}
                        </td>
                        <td className="px-3 py-2 mono text-text-muted">
                          {f.sha256 ? f.sha256.slice(0, 16) + "…" : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-text-muted">No files in export package.</p>
            )}
          </div>
        ) : (
          <p className="text-sm text-text-muted">No export manifest available.</p>
        )}
      </Card>
    </>
  );
}
