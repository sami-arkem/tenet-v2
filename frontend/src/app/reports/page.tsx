"use client";

// Reports screen — Bible §15
// Lists generated audit reports. Generate + download from here.

import { useState, useCallback } from "react";
import useSWR from "swr";
import { useAuth } from "@/contexts/AuthContext";
import { listAudits } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { PageSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { AuditSummary, AuditDetail } from "@/lib/types";
import {
  FileText,
  Download,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from "lucide-react";

const BASE = "/api/proxy";

async function generateReport(
  userId: string,
  auditRunId: string,
): Promise<{ report_id: string; download_urls: Record<string, string> }> {
  const token = sessionStorage.getItem("tenet:access_token");
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token && !token.startsWith("dev:")) {
    headers["Authorization"] = `Bearer ${token}`;
  } else {
    headers["X-User-ID"] = userId;
  }
  const res = await fetch(`${BASE}/v1/reports/generate`, {
    method: "POST",
    headers,
    body: JSON.stringify({ audit_run_id: auditRunId }),
  });
  const json = await res.json();
  if (!res.ok || json.error) throw new Error(json.error?.message ?? "Failed to generate report");
  return json.data;
}

// ─── Verdict icon ─────────────────────────────────────────────────────────────
function VerdictIcon({ verdict }: { verdict: string | null }) {
  if (verdict === "PASS") return <CheckCircle2 className="h-4 w-4 text-success-base" />;
  if (verdict === "FAIL") return <XCircle className="h-4 w-4 text-danger-base" />;
  if (verdict === "PARTIAL") return <AlertCircle className="h-4 w-4 text-warning-base" />;
  return <AlertCircle className="h-4 w-4 text-neutral-400" />;
}

// ─── Report card ──────────────────────────────────────────────────────────────
function ReportCard({ audit, userId }: { audit: AuditSummary & { latest_run_id?: string | null }; userId: string }) {
  const [generating, setGenerating] = useState(false);
  const [reportId, setReportId] = useState<string | null>(null);
  const [downloadUrls, setDownloadUrls] = useState<Record<string, string> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isComplete = audit.status === "COMPLETED" || audit.status === "BLOCKED";
  const latestRunId = audit.latest_run_id ?? null;

  async function handleGenerate() {
    if (!latestRunId) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await generateReport(userId, latestRunId);
      setReportId(result.report_id);
      setDownloadUrls(result.download_urls);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to generate report");
    } finally {
      setGenerating(false);
    }
  }

  function download(url: string, filename: string) {
    const a = document.createElement("a");
    a.href = `${BASE}${url}`;
    a.download = filename;
    a.click();
  }

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <FileText className="h-5 w-5 text-neutral-400 mt-0.5 shrink-0" />
          <div>
            <div className="text-14 font-medium text-neutral-800">
              {audit.system_name}
            </div>
            <div className="text-12 text-neutral-500 mt-0.5">
              {audit.audit_kind} · {audit.jurisdiction} · {audit.framework}
            </div>
            <div className="flex items-center gap-3 mt-2">
              <Badge variant={audit.status as never} />
              {audit.deployment_decision && (
                <Badge variant={audit.deployment_decision as never} />
              )}
              <span className="text-12 text-neutral-400">
                {formatDate(audit.updated_at)}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {!isComplete ? (
            <span className="text-12 text-neutral-400">Audit not complete</span>
          ) : !latestRunId ? (
            <span className="text-12 text-neutral-400">No run yet</span>
          ) : downloadUrls ? (
            <div className="flex items-center gap-2">
              <button
                onClick={() => download(downloadUrls.json, `tenet_report_${reportId?.slice(0, 8)}.json`)}
                className="flex items-center gap-1.5 text-13 text-brand-600 hover:text-brand-700"
              >
                <Download className="h-4 w-4" />
                JSON
              </button>
              <button
                onClick={() => download(downloadUrls.text, `tenet_report_${reportId?.slice(0, 8)}.txt`)}
                className="flex items-center gap-1.5 text-13 text-brand-600 hover:text-brand-700"
              >
                <Download className="h-4 w-4" />
                Text
              </button>
            </div>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleGenerate}
              loading={generating}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Generate Report
            </Button>
          )}
        </div>
      </div>

      {error && (
        <p className="mt-3 text-13 text-danger-dark">{error}</p>
      )}

      {downloadUrls && (
        <div className="mt-3 flex items-center gap-2 text-12 text-success-dark bg-success-light rounded px-3 py-2">
          <CheckCircle2 className="h-3.5 w-3.5 text-success-base" />
          Report generated — report ID: <span className="font-mono">{reportId?.slice(0, 16)}…</span>
        </div>
      )}
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const { userId } = useAuth();

  const { data, error, isLoading, mutate } = useSWR(
    userId ? ["audits-for-reports", userId] : null,
    ([, uid]) => listAudits(uid),
    { refreshInterval: 30_000 },
  );

  if (isLoading) return <PageSkeleton />;
  if (error)
    return <ErrorMessage message={error.message} onRetry={() => mutate()} />;

  const audits = data ?? [];
  const completedAudits = audits.filter(
    (a) => a.status === "COMPLETED" || a.status === "BLOCKED",
  );

  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Generate and download compliance audit reports"
      />

      {completedAudits.length === 0 ? (
        <EmptyState
          icon={<FileText size={24} />}
          title="No completed audits"
          description="Complete an audit to generate a compliance report."
          action={
            <Button variant="primary" size="sm" onClick={() => window.location.href = "/audits/new"}>
              Start an Audit
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {completedAudits.map((audit) => (
            <ReportCard key={audit.audit_id} audit={audit} userId={userId!} />
          ))}
        </div>
      )}
    </>
  );
}
