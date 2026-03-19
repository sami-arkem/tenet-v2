// ─── API Envelope ────────────────────────────────────────────────────────────

export interface ApiMeta {
  request_id: string;
  timestamp: string;
  version: string;
  run_id: string | null;
}

export interface ApiError {
  code: string;
  message: string;
  details: Record<string, unknown> | null;
}

export interface ApiResponse<T> {
  data: T | null;
  meta: ApiMeta;
  error: ApiError | null;
}

// ─── Audit ───────────────────────────────────────────────────────────────────

export type AuditStatus = "CREATED" | "QUEUED" | "RUNNING" | "COMPLETED" | "BLOCKED";
export type DeploymentDecision = "APPROVED" | "CONDITIONALLY_APPROVED" | "BLOCKED" | "UNKNOWN";

export interface AuditSummary {
  audit_id: string;
  tenant_id: string;
  audit_kind: string;
  entity_id: string;
  system_name: string;
  jurisdiction: string;
  framework: string;
  status: AuditStatus;
  deployment_decision: DeploymentDecision;
  release_ready: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuditDetail extends AuditSummary {
  report_ready: boolean;
  export_ready: boolean;
  finalization_ready: boolean;
  note: string | null;
  latest_run_id: string | null;
}

export interface CreateAuditRequest {
  audit_kind: string;
  entity_id: string;
  system_name: string;
  jurisdiction: string;
  framework: string;
  scheduled_date?: string | null;
  note?: string | null;
}

export interface AuditRunSummary {
  run_id: string;
  audit_id: string;
  tenant_id: string;
  status: string;
  deployment_decision: DeploymentDecision;
  report_ready: boolean;
  export_ready: boolean;
  finalization_ready: boolean;
  started_at: string | null;
  completed_at: string | null;
}

export interface ReleaseSummary {
  audit_id: string;
  release_status: string;
  release_ready: boolean;
  finalization_status: string;
  finalization_ready: boolean;
  remediation_gate_status: string | null;
  remediation_ready: boolean | null;
  blocking_reasons: string[];
}

// ─── Audit Preparation ───────────────────────────────────────────────────────

export type ChecklistStatus =
  | "MISSING"
  | "UPLOADING"
  | "PROCESSING"
  | "READY"
  | "OCR_REQUIRED"
  | "REVIEW_REQUIRED"
  | "FAILED";

export type PreparationStatus = "BLOCKED" | "READY";

export interface EvidenceChecklistItem {
  requirement_id: string;
  audit_id: string;
  tenant_id: string;
  audit_kind: string;
  framework: string;
  required_category: string;
  label: string;
  status: ChecklistStatus;
  linked_evidence_ids: string[];
  blocking_reasons: string[];
  predicted_categories: string[];
  final_categories: string[];
}

export interface AuditPreparationSummary {
  audit_id: string;
  tenant_id: string;
  preparation_status: PreparationStatus;
  total_requirements: number;
  total_ready: number;
  total_blocked: number;
  checklist: EvidenceChecklistItem[];
  blocking_reasons: string[];
}

export interface ModelCallLogRow {
  call_id: string;
  tenant_id: string;
  audit_id: string;
  evidence_id: string | null;
  surface: string;
  model_name: string;
  action: string;
  status: string;
  input_ref: string | null;
  output_ref: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

// ─── Evidence ────────────────────────────────────────────────────────────────

export type EvidenceStatus = "UPLOADING" | "PROCESSING" | "READY" | "FAILED" | "CANCELLED";

export interface EvidenceSummary {
  evidence_id: string;
  audit_id: string;
  tenant_id: string;
  filename: string;
  content_type: string;
  sha256: string;
  byte_size: number;
  evidence_category: string;
  status: EvidenceStatus;
  supersedes_id: string | null;
  version_number: number;
  created_at: string;
  updated_at: string;
}

export interface EvidenceDetail extends EvidenceSummary {
  storage_path: string | null;
  processing_error: string | null;
  extracted_text_ready: boolean;
  inventory_ready: boolean;
  immutable_after_ready: boolean;
  note: string | null;
}

export interface EvidenceListResponse {
  audit_id: string | null;
  total_items: number;
  total_ready: number;
  total_processing: number;
  total_failed: number;
  total_cancelled: number;
  rows: EvidenceSummary[];
}

export interface AuditEvidenceGateResponse {
  audit_id: string;
  gate_name: string;
  gate_status: string;
  evidence_ready: boolean;
  waiting_file_count: number;
  total_files: number;
  total_ready_files: number;
  blocking_reasons: string[];
  required_categories: string[];
  ready_categories: string[];
}

// ─── Upload Sessions ─────────────────────────────────────────────────────────

export type UploadSessionStatus =
  | "CREATED"
  | "UPLOADING"
  | "FINALIZING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export interface UploadSessionSummary {
  upload_session_id: string;
  audit_id: string;
  tenant_id: string;
  filename: string;
  content_type: string;
  sha256: string;
  byte_size: number;
  evidence_category: string;
  status: UploadSessionStatus;
  blob_id: string | null;
  storage_path: string | null;
  evidence_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface UploadSessionListResponse {
  total_items: number;
  total_created: number;
  total_uploading: number;
  total_finalizing: number;
  total_completed: number;
  total_failed: number;
  total_cancelled: number;
  rows: UploadSessionSummary[];
}

export interface CreateUploadSessionRequest {
  audit_id: string;
  filename: string;
  content_type: string;
  sha256: string;
  byte_size: number;
  evidence_category: string;
  note?: string | null;
  supersedes_id?: string | null;
}

// ─── Evidence Jobs ───────────────────────────────────────────────────────────

export type EvidenceJobStatus = "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface EvidenceJobSummary {
  job_id: string;
  evidence_id: string;
  audit_id: string | null;
  tenant_id: string;
  status: EvidenceJobStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface EvidenceJobListResponse {
  total_items: number;
  total_queued: number;
  total_processing: number;
  total_completed: number;
  total_failed: number;
  rows: EvidenceJobSummary[];
}

// ─── Findings ────────────────────────────────────────────────────────────────

export interface FindingRow {
  finding_id: string;
  audit_id: string;
  tenant_id: string;
  finding_type: string;
  title: string;
  detail: string;
  severity: string;
}

export interface FindingListResponse {
  audit_id: string;
  total_findings: number;
  rows: FindingRow[];
}

export interface FindingsSummary {
  audit_id: string;
  total_findings: number;
  total_missing_controls: number;
  total_missing_evidence: number;
  blocking_reasons: string[];
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export interface ReportSummaryResponse {
  audit_id: string;
  run_id: string | null;
  report_ready: boolean;
  export_ready: boolean;
  finalization_ready: boolean;
  release_ready: boolean;
  release_status: string;
  finalization_status: string;
  remediation_gate_status: string | null;
  blocking_reasons: string[];
}

export interface ExportManifestSummaryResponse {
  audit_id: string;
  package_status: string;
  package_ready: boolean;
  manifest_path: string;
  included_files: Array<{ path: string; sha256?: string; size?: number }>;
  blocking_reasons: string[];
}

// ─── Remediation ─────────────────────────────────────────────────────────────

export interface RemediationItem {
  remediation_id: string;
  finding_id: string;
  audit_id: string;
  tenant_id: string;
  title: string;
  gap_note: string;
  status: string;
  severity: string;
  release_blocking: boolean;
  owner_user_id: string | null;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface RemediationDashboard {
  tenant_id: string;
  actor_user_id: string;
  today: string;
  total_items: number;
  overdue: RemediationItem[];
  due_soon: RemediationItem[];
  in_progress: RemediationItem[];
  open: RemediationItem[];
  resolved: RemediationItem[];
  not_applicable: RemediationItem[];
  release_blocking_count: number;
  overdue_count: number;
}

export interface TimelineEvent {
  event_id: string;
  remediation_id: string;
  tenant_id: string;
  actor_user_id: string;
  event_type: string;
  note: string | null;
  to_status: string | null;
  evidence_files: Array<{
    file_id: string;
    filename: string;
    content_type: string;
    sha256: string;
    byte_size: number;
  }>;
  created_at: string;
}

export interface RemediationDetail {
  item: RemediationItem;
  timeline: TimelineEvent[];
  evidence_metadata: unknown[];
}
