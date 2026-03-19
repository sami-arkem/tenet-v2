"use client";

import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  listUploadSessions,
  listEvidence,
  createUploadSession,
  cancelUploadSession,
  listEvidenceJobs,
  runNextJob,
  getAudit,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { DataTable } from "@/components/ui/DataTable";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Button } from "@/components/ui/Button";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { PageSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { StatRow } from "@/components/ui/StatRow";
import { formatBytes, formatDate } from "@/lib/utils";
import { useState } from "react";
import type {
  UploadSessionSummary,
  EvidenceSummary,
  CreateUploadSessionRequest,
} from "@/lib/types";
import { Upload, Play, X } from "lucide-react";
import { cn } from "@/lib/utils";

const EVIDENCE_CATEGORIES = [
  "policy",
  "governance",
  "risk_assessment",
  "training",
  "transaction_records",
  "customer_records",
  "controls_documentation",
  "audit_trail",
  "other",
];

const INPUT_CLS = cn(
  "w-full px-3 py-2 border border-neutral-200 rounded-base bg-white",
  "text-14 text-neutral-800 placeholder:text-neutral-400",
  "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500",
  "transition-colors duration-base",
);

const LABEL_CLS = "block text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1.5";

function CreateSessionForm({
  auditId,
  userId,
  onCreated,
}: {
  auditId: string;
  userId: string;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<Omit<CreateUploadSessionRequest, "audit_id">>({
    filename: "",
    content_type: "application/pdf",
    sha256: "",
    byte_size: 0,
    evidence_category: "policy",
    note: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.filename || !form.sha256 || form.byte_size <= 0) {
      setError("Filename, SHA-256, and byte size are required.");
      return;
    }
    if (form.sha256.length < 32) {
      setError("SHA-256 must be at least 32 characters.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await createUploadSession(userId, {
        ...form,
        audit_id: auditId,
        filename: form.filename,
        sha256: form.sha256,
        byte_size: form.byte_size,
      });
      setForm({
        filename: "",
        content_type: "application/pdf",
        sha256: "",
        byte_size: 0,
        evidence_category: "policy",
        note: null,
      });
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create session.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1.5">
            Filename <span className="text-danger-base">*</span>
          </label>
          <input
            type="text"
            className={INPUT_CLS}
            placeholder="aml_policy_2024.pdf"
            value={form.filename}
            onChange={(e) => setForm((f) => ({ ...f, filename: e.target.value }))}
          />
        </div>
        <div>
          <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1.5">
            Content Type
          </label>
          <select
            className={INPUT_CLS}
            value={form.content_type}
            onChange={(e) => setForm((f) => ({ ...f, content_type: e.target.value }))}
          >
            <option value="application/pdf">PDF</option>
            <option value="application/vnd.openxmlformats-officedocument.wordprocessingml.document">DOCX</option>
            <option value="application/json">JSON</option>
            <option value="text/csv">CSV</option>
            <option value="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet">XLSX</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1.5">
            SHA-256 Hash <span className="text-danger-base">*</span>
          </label>
          <input
            type="text"
            className={`${INPUT_CLS} mono`}
            placeholder="Hex hash of the file contents"
            value={form.sha256}
            onChange={(e) => setForm((f) => ({ ...f, sha256: e.target.value }))}
          />
        </div>
        <div>
          <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1.5">
            Byte Size <span className="text-danger-base">*</span>
          </label>
          <input
            type="number"
            className={INPUT_CLS}
            placeholder="Bytes"
            min={1}
            value={form.byte_size || ""}
            onChange={(e) =>
              setForm((f) => ({ ...f, byte_size: parseInt(e.target.value, 10) || 0 }))
            }
          />
        </div>
      </div>

      <div>
        <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1.5">
          Evidence Category
        </label>
        <select
          className={INPUT_CLS}
          value={form.evidence_category}
          onChange={(e) => setForm((f) => ({ ...f, evidence_category: e.target.value }))}
        >
          {EVIDENCE_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p className="text-14 text-danger-dark bg-danger-light border border-danger-base/20 rounded-base px-3 py-2">
          {error}
        </p>
      )}

      <Button type="submit" variant="primary" size="sm" loading={loading}>
        <Upload size={12} />
        Create Upload Session
      </Button>
    </form>
  );
}

export default function EvidenceIntakePage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { userId } = useAuth();
  const [cancelId, setCancelId] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [jobLoading, setJobLoading] = useState(false);

  const { data: audit } = useSWR(
    userId && auditId ? ["audit", auditId, userId] : null,
    ([, id, uid]) => getAudit(uid, id),
  );

  const {
    data: sessions,
    error: sessionsError,
    isLoading: sessionsLoading,
    mutate: mutateSessions,
  } = useSWR(
    userId && auditId ? ["upload-sessions", auditId, userId] : null,
    ([, id, uid]) => listUploadSessions(uid, id),
    { refreshInterval: 8_000 },
  );

  const {
    data: evidence,
    error: evidenceError,
    isLoading: evidenceLoading,
    mutate: mutateEvidence,
  } = useSWR(
    userId && auditId ? ["evidence", auditId, userId] : null,
    ([, id, uid]) => listEvidence(uid, id),
    { refreshInterval: 8_000 },
  );

  const { data: jobs, mutate: mutateJobs } = useSWR(
    userId ? ["jobs", userId] : null,
    ([, uid]) => listEvidenceJobs(uid),
    { refreshInterval: 8_000 },
  );

  async function handleCancel(sessionId: string) {
    setCancelling(true);
    try {
      await cancelUploadSession(userId!, sessionId);
      await mutateSessions();
    } finally {
      setCancelling(false);
      setCancelId(null);
    }
  }

  async function handleRunJob() {
    setJobLoading(true);
    try {
      await runNextJob(userId!);
      await mutateJobs();
      await mutateEvidence();
    } finally {
      setJobLoading(false);
    }
  }

  if (sessionsLoading || evidenceLoading) return <PageSkeleton />;

  return (
    <>
      <PageHeader
        title="Evidence Intake"
        subtitle={audit?.system_name}
        breadcrumbs={[
          { label: "Audits", href: "/audits" },
          { label: audit?.system_name ?? auditId, href: `/audits/${auditId}` },
          { label: "Evidence" },
        ]}
        action={
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRunJob}
            loading={jobLoading}
          >
            <Play size={12} />
            Run Next Job
          </Button>
        }
      />

      {/* Upload session create form */}
      <Card className="mb-6">
        <SectionHeader
          title="New Upload Session"
          subtitle="Create an upload session to register a file. The session must be finalized before evidence is processed."
        />
        <CreateSessionForm
          auditId={auditId}
          userId={userId!}
          onCreated={() => mutateSessions()}
        />
      </Card>

      {/* Session stats */}
      {sessions && (
        <Card className="mb-6">
          <StatRow
            stats={[
              { label: "total", value: sessions.total_items },
              { label: "created", value: sessions.total_created, variant: "muted" },
              { label: "completed", value: sessions.total_completed, variant: "success" },
              { label: "failed", value: sessions.total_failed, variant: sessions.total_failed > 0 ? "error" : "muted" },
              { label: "cancelled", value: sessions.total_cancelled, variant: "muted" },
            ]}
          />
        </Card>
      )}

      {/* Upload sessions table */}
      <Card className="mb-6" padding={false}>
        <div className="px-5 py-4 border-b border-neutral-200">
          <SectionHeader
            title="Upload Sessions"
            subtitle="COMPLETED means the file is in blob storage. It does not mean evidence is processed or ready."
          />
        </div>
        {sessionsError ? (
          <ErrorMessage message={sessionsError.message} onRetry={() => mutateSessions()} />
        ) : (
          <DataTable<UploadSessionSummary>
            columns={[
              {
                key: "filename",
                header: "Filename",
                render: (row) => (
                  <div>
                    <div className="text-neutral-800">{row.filename}</div>
                    <div className="text-12 mono text-neutral-400">{row.upload_session_id}</div>
                  </div>
                ),
              },
              {
                key: "category",
                header: "Category",
                width: "140px",
                render: (row) => (
                  <span className="mono text-12 text-neutral-500">
                    {row.evidence_category}
                  </span>
                ),
              },
              {
                key: "size",
                header: "Size",
                width: "80px",
                render: (row) => (
                  <span className="text-neutral-400 text-xs">
                    {formatBytes(row.byte_size)}
                  </span>
                ),
              },
              {
                key: "status",
                header: "Status",
                width: "110px",
                render: (row) => <Badge variant={row.status} />,
              },
              {
                key: "evidence_id",
                header: "Evidence ID",
                width: "160px",
                render: (row) => (
                  <span className="mono text-13 text-neutral-400">
                    {row.evidence_id ?? "—"}
                  </span>
                ),
              },
              {
                key: "updated_at",
                header: "Updated",
                width: "150px",
                render: (row) => (
                  <span className="text-13 text-neutral-400">
                    {formatDate(row.updated_at)}
                  </span>
                ),
              },
              {
                key: "actions",
                header: "",
                width: "40px",
                render: (row) =>
                  row.status === "CREATED" || row.status === "UPLOADING" ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setCancelId(row.upload_session_id);
                      }}
                      className="text-neutral-400 hover:text-danger-dark transition-colors duration-base"
                      title="Cancel session"
                    >
                      <X size={13} />
                    </button>
                  ) : null,
              },
            ]}
            rows={sessions?.rows ?? []}
            getKey={(row) => row.upload_session_id}
            emptyState="No upload sessions for this audit."
          />
        )}
      </Card>

      {/* Evidence list */}
      <Card className="mb-6" padding={false}>
        <div className="px-5 py-4 border-b border-neutral-200">
          <div className="flex items-start justify-between">
            <SectionHeader
              title="Evidence Items"
              subtitle="Evidence is READY only after processing completes successfully."
            />
            {evidence && (
              <StatRow
                stats={[
                  { label: "total", value: evidence.total_items },
                  { label: "ready", value: evidence.total_ready, variant: "success" },
                  { label: "processing", value: evidence.total_processing, variant: "default" },
                  { label: "failed", value: evidence.total_failed, variant: evidence.total_failed > 0 ? "error" : "muted" },
                ]}
              />
            )}
          </div>
        </div>
        {evidenceError ? (
          <ErrorMessage message={evidenceError.message} onRetry={() => mutateEvidence()} />
        ) : (
          <DataTable<EvidenceSummary>
            columns={[
              {
                key: "filename",
                header: "Filename",
                render: (row) => (
                  <div>
                    <div className="text-neutral-800">{row.filename}</div>
                    <div className="mono text-13 text-neutral-400">
                      {row.evidence_id}
                    </div>
                  </div>
                ),
              },
              {
                key: "category",
                header: "Category",
                width: "140px",
                render: (row) => (
                  <span className="mono text-12 text-neutral-500">
                    {row.evidence_category}
                  </span>
                ),
              },
              {
                key: "size",
                header: "Size",
                width: "80px",
                render: (row) => (
                  <span className="text-neutral-400 text-xs">
                    {formatBytes(row.byte_size)}
                  </span>
                ),
              },
              {
                key: "version",
                header: "Ver",
                width: "50px",
                render: (row) => (
                  <span className="text-neutral-400 text-xs">v{row.version_number}</span>
                ),
              },
              {
                key: "status",
                header: "Status",
                width: "110px",
                render: (row) => <Badge variant={row.status} />,
              },
              {
                key: "updated_at",
                header: "Updated",
                width: "150px",
                render: (row) => (
                  <span className="text-13 text-neutral-400">
                    {formatDate(row.updated_at)}
                  </span>
                ),
              },
            ]}
            rows={evidence?.rows ?? []}
            getKey={(row) => row.evidence_id}
            emptyState="No evidence registered for this audit."
          />
        )}
      </Card>

      {/* Processing jobs */}
      {jobs && jobs.total_items > 0 && (
        <Card padding={false}>
          <div className="px-5 py-4 border-b border-neutral-200">
            <SectionHeader
              title="Processing Jobs"
              subtitle={`${jobs.total_queued} queued · ${jobs.total_processing} processing · ${jobs.total_failed} failed`}
            />
          </div>
          <DataTable
            columns={[
              {
                key: "job_id",
                header: "Job ID",
                render: (row) => (
                  <span className="mono text-13 text-neutral-400">{row.job_id}</span>
                ),
              },
              {
                key: "evidence_id",
                header: "Evidence ID",
                width: "180px",
                render: (row) => (
                  <span className="mono text-13 text-neutral-400">{row.evidence_id}</span>
                ),
              },
              {
                key: "status",
                header: "Status",
                width: "110px",
                render: (row) => <Badge variant={row.status as string} />,
              },
              {
                key: "error",
                header: "Error",
                render: (row) =>
                  row.error_message ? (
                    <span className="text-xs text-danger-dark">{String(row.error_message)}</span>
                  ) : (
                    <span className="text-neutral-400">—</span>
                  ),
              },
              {
                key: "updated_at",
                header: "Updated",
                width: "150px",
                render: (row) => (
                  <span className="text-13 text-neutral-400">
                    {formatDate(String(row.updated_at))}
                  </span>
                ),
              },
            ]}
            rows={jobs.rows}
            getKey={(row) => row.job_id}
          />
        </Card>
      )}

      {/* Cancel confirmation modal */}
      <ConfirmModal
        open={cancelId !== null}
        title="Cancel upload session?"
        description="This will cancel the upload session. Files already uploaded will not be processed."
        confirmLabel="Cancel Session"
        destructive
        onConfirm={() => cancelId && handleCancel(cancelId)}
        onCancel={() => setCancelId(null)}
      />
    </>
  );
}
