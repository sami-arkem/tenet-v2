/**
 * Tenet API client
 * All requests go through /api/proxy/* (Next.js rewrite → backend).
 * Auth is X-User-ID header only — the backend uses an actor directory.
 * No fake data. No invented states. Every function maps to a real route.
 */

import type {
  ApiResponse,
  AuditSummary,
  AuditDetail,
  CreateAuditRequest,
  AuditRunSummary,
  ReleaseSummary,
  FindingsSummary,
  AuditPreparationSummary,
  ModelCallLogRow,
  EvidenceListResponse,
  EvidenceDetail,
  EvidenceGateResponse,
  UploadSessionListResponse,
  UploadSessionSummary,
  CreateUploadSessionRequest,
  EvidenceJobListResponse,
  FindingListResponse,
  ReportSummaryResponse,
  ExportManifestSummaryResponse,
  RemediationItem,
  RemediationDashboard,
  RemediationDetail,
  AuditEvidenceGateResponse,
} from "./types";

const BASE = "/api/proxy";

class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  userId: string,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-User-ID": userId,
    ...(init.headers as Record<string, string>),
  };

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
  });

  const envelope: ApiResponse<T> = await res.json();

  if (!res.ok || envelope.error) {
    throw new ApiError(
      envelope.error?.code ?? "HTTP_ERROR",
      envelope.error?.message ?? `HTTP ${res.status}`,
      res.status,
    );
  }

  return envelope.data as T;
}

// ─── Audits ──────────────────────────────────────────────────────────────────

export function listAudits(userId: string): Promise<AuditSummary[]> {
  return request<AuditSummary[]>("/v1/audits", {}, userId);
}

export function createAudit(
  userId: string,
  body: CreateAuditRequest,
): Promise<AuditSummary> {
  return request<AuditSummary>(
    "/v1/audits",
    { method: "POST", body: JSON.stringify(body) },
    userId,
  );
}

export function getAudit(userId: string, auditId: string): Promise<AuditDetail> {
  return request<AuditDetail>(`/v1/audits/${auditId}`, {}, userId);
}

export function triggerAuditRun(
  userId: string,
  auditId: string,
): Promise<{ audit_id: string; run_id: string; queue_status: string; message: string }> {
  return request(`/v1/audits/${auditId}/run`, { method: "POST" }, userId);
}

export function getLatestRun(
  userId: string,
  auditId: string,
): Promise<AuditRunSummary> {
  return request<AuditRunSummary>(
    `/v1/audits/${auditId}/runs/latest`,
    {},
    userId,
  );
}

export function syncFindings(
  userId: string,
  auditId: string,
): Promise<FindingsSummary> {
  return request<FindingsSummary>(
    `/v1/audits/${auditId}/findings/sync`,
    { method: "POST" },
    userId,
  );
}

export function getReleaseSummary(
  userId: string,
  auditId: string,
): Promise<ReleaseSummary> {
  return request<ReleaseSummary>(`/v1/audits/${auditId}/release`, {}, userId);
}

// ─── Audit Preparation ───────────────────────────────────────────────────────

export function getPreparationSummary(
  userId: string,
  auditId: string,
): Promise<AuditPreparationSummary> {
  return request<AuditPreparationSummary>(
    `/v1/audit-preparation/${auditId}`,
    {},
    userId,
  );
}

export function ensureRequirements(
  userId: string,
  auditId: string,
): Promise<{ audit_id: string; requirements: unknown[] }> {
  return request(
    `/v1/audit-preparation/${auditId}/requirements/ensure`,
    { method: "POST" },
    userId,
  );
}

export function listModelCalls(
  userId: string,
  auditId: string,
): Promise<ModelCallLogRow[]> {
  return request<ModelCallLogRow[]>(
    `/v1/audit-preparation/${auditId}/model-calls`,
    {},
    userId,
  );
}

// ─── Evidence ────────────────────────────────────────────────────────────────

export function listEvidence(
  userId: string,
  auditId?: string,
): Promise<EvidenceListResponse> {
  const qs = auditId ? `?audit_id=${encodeURIComponent(auditId)}` : "";
  return request<EvidenceListResponse>(`/v1/evidence${qs}`, {}, userId);
}

export function getEvidence(
  userId: string,
  evidenceId: string,
): Promise<EvidenceDetail> {
  return request<EvidenceDetail>(`/v1/evidence/${evidenceId}`, {}, userId);
}

export function recomputeGate(
  userId: string,
  auditId: string,
): Promise<AuditEvidenceGateResponse> {
  return request<AuditEvidenceGateResponse>(
    `/v1/evidence/audits/${auditId}/gate/recompute`,
    { method: "POST" },
    userId,
  );
}

export function submitOcrText(
  userId: string,
  evidenceId: string,
  ocrText: string,
): Promise<{ evidence_id: string; stored_path: string; message: string }> {
  return request(
    `/v1/ocr-submissions/${evidenceId}`,
    { method: "POST", body: JSON.stringify({ ocr_text: ocrText }) },
    userId,
  );
}

// ─── Upload Sessions ─────────────────────────────────────────────────────────

export function listUploadSessions(
  userId: string,
  auditId?: string,
): Promise<UploadSessionListResponse> {
  const qs = auditId ? `?audit_id=${encodeURIComponent(auditId)}` : "";
  return request<UploadSessionListResponse>(
    `/v1/upload-sessions${qs}`,
    {},
    userId,
  );
}

export function createUploadSession(
  userId: string,
  body: CreateUploadSessionRequest,
): Promise<UploadSessionSummary> {
  return request<UploadSessionSummary>(
    "/v1/upload-sessions",
    { method: "POST", body: JSON.stringify(body) },
    userId,
  );
}

export function finalizeUploadSession(
  userId: string,
  sessionId: string,
  tempFilePath: string,
): Promise<UploadSessionSummary> {
  return request<UploadSessionSummary>(
    `/v1/upload-sessions/${sessionId}/finalize`,
    {
      method: "POST",
      body: JSON.stringify({ temp_file_path: tempFilePath }),
    },
    userId,
  );
}

export function failUploadSession(
  userId: string,
  sessionId: string,
  errorMessage: string,
): Promise<UploadSessionSummary> {
  return request<UploadSessionSummary>(
    `/v1/upload-sessions/${sessionId}/fail`,
    {
      method: "POST",
      body: JSON.stringify({ error_message: errorMessage }),
    },
    userId,
  );
}

export function cancelUploadSession(
  userId: string,
  sessionId: string,
): Promise<UploadSessionSummary> {
  return request<UploadSessionSummary>(
    `/v1/upload-sessions/${sessionId}/cancel`,
    { method: "POST", body: JSON.stringify({}) },
    userId,
  );
}

// ─── Evidence Jobs ───────────────────────────────────────────────────────────

export function listEvidenceJobs(
  userId: string,
  status?: string,
): Promise<EvidenceJobListResponse> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<EvidenceJobListResponse>(`/v1/evidence-jobs${qs}`, {}, userId);
}

export function runNextJob(
  userId: string,
): Promise<{ status: string } | Record<string, unknown>> {
  return request(`/v1/evidence-jobs/run-next`, { method: "POST" }, userId);
}

// ─── Findings ────────────────────────────────────────────────────────────────

export function listFindings(
  userId: string,
  auditId: string,
): Promise<FindingListResponse> {
  return request<FindingListResponse>(
    `/v1/findings/audit/${auditId}`,
    {},
    userId,
  );
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export function getReportSummary(
  userId: string,
  auditId: string,
): Promise<ReportSummaryResponse> {
  return request<ReportSummaryResponse>(
    `/v1/reports/${auditId}/summary`,
    {},
    userId,
  );
}

export function getExportManifest(
  userId: string,
  auditId: string,
): Promise<ExportManifestSummaryResponse> {
  return request<ExportManifestSummaryResponse>(
    `/v1/reports/${auditId}/export-manifest`,
    {},
    userId,
  );
}

// ─── Remediation ─────────────────────────────────────────────────────────────

export function getRemediationDashboard(
  userId: string,
  today?: string,
): Promise<RemediationDashboard> {
  const qs = today ? `?today=${encodeURIComponent(today)}` : "";
  return request<RemediationDashboard>(
    `/v1/remediation/dashboard${qs}`,
    {},
    userId,
  );
}

export function listRemediations(
  userId: string,
): Promise<RemediationItem[]> {
  return request<RemediationItem[]>("/v1/remediation", {}, userId);
}

export function getRemediationDetail(
  userId: string,
  remediationId: string,
): Promise<RemediationDetail> {
  return request<RemediationDetail>(
    `/v1/remediation/${remediationId}`,
    {},
    userId,
  );
}

export function assignRemediationOwner(
  userId: string,
  remediationId: string,
  ownerUserId: string,
  note: string,
): Promise<unknown> {
  return request(
    `/v1/remediation/${remediationId}/assign-owner`,
    {
      method: "POST",
      body: JSON.stringify({ owner_user_id: ownerUserId, note }),
    },
    userId,
  );
}

export function setRemediationDueDate(
  userId: string,
  remediationId: string,
  dueDate: string,
  note: string,
): Promise<unknown> {
  return request(
    `/v1/remediation/${remediationId}/due-date`,
    {
      method: "POST",
      body: JSON.stringify({ due_date: dueDate, note }),
    },
    userId,
  );
}

export function transitionRemediationStatus(
  userId: string,
  remediationId: string,
  toStatus: string,
  note: string,
  evidenceFiles: unknown[] = [],
): Promise<unknown> {
  return request(
    `/v1/remediation/${remediationId}/status`,
    {
      method: "POST",
      body: JSON.stringify({
        to_status: toStatus,
        note,
        evidence_files: evidenceFiles,
      }),
    },
    userId,
  );
}

export function applyVerificationResult(
  userId: string,
  remediationId: string,
  verificationPassed: boolean,
  updatedGapNote?: string,
): Promise<unknown> {
  return request(
    `/v1/remediation/${remediationId}/verification-result`,
    {
      method: "POST",
      body: JSON.stringify({
        verification_passed: verificationPassed,
        updated_gap_note: updatedGapNote ?? null,
      }),
    },
    userId,
  );
}

export { ApiError };
