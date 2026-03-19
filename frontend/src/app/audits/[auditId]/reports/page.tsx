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
import { Badge } from "@/components/ui/Badge";
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
    <div className="flex items-center justify-between py-2.5 border-b border-neutral-200 last:border-0">
      <div className="flex items-center gap-2.5">
        {ready ? (
          <CheckCircle2 size={14} className="text-success-base flex-none" />
        ) : (
          <XCircle size={14} className="text-danger-base flex-none" />
        )}
        <span className="text-14 text-neutral-800">{label}</span>
      </div>
      {status && <Badge variant={status} />}
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
  const uniqueBlocking = allBlocking.filter((v, i, a) => a.indexOf(v) === i);

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
                <div className="mt-4 pt-3 border-t border-neutral-200">
                  <div className="text-13 text-neutral-400 uppercase tracking-wide mb-1">Run ID</div>
                  <div className="mono text-12 text-neutral-500">{report.run_id}</div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-neutral-400">No report data available. Run the audit first.</p>
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
            <p className="text-sm text-neutral-400">No release data. Complete the audit run.</p>
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
              <Package size={15} className="text-neutral-500" />
              <div>
                <div className="text-14 text-neutral-800 font-medium">
                  {manifest.package_status}
                </div>
                <div className="text-13 text-neutral-400 mono">{manifest.manifest_path}</div>
              </div>
              <Badge variant={manifest.package_ready ? "ready" : "blocked"} />
            </div>

            {manifest.included_files.length > 0 ? (
              <div className="border border-neutral-200 rounded overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-neutral-50 border-b border-neutral-200">
                    <tr>
                      <th className="px-3 py-2 text-left text-neutral-400 font-medium">File</th>
                      <th className="px-3 py-2 text-left text-neutral-400 font-medium w-24">Size</th>
                      <th className="px-3 py-2 text-left text-neutral-400 font-medium w-48">SHA-256</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100 bg-white">
                    {manifest.included_files.map((f, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 mono text-neutral-500">
                          <FileText size={12} className="inline mr-1.5 text-neutral-400" />
                          {f.path}
                        </td>
                        <td className="px-3 py-2 text-neutral-400">
                          {f.size != null ? formatBytes(f.size) : "—"}
                        </td>
                        <td className="px-3 py-2 mono text-neutral-400">
                          {f.sha256 ? f.sha256.slice(0, 16) + "…" : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-neutral-400">No files in export package.</p>
            )}
          </div>
        ) : (
          <p className="text-sm text-neutral-400">No export manifest available.</p>
        )}
      </Card>
    </>
  );
}
