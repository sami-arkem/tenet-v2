-- =============================================================================
-- TENET DATABASE SCHEMA — v1.0
-- Bible §5: The Complete Database Schema
-- PostgreSQL 14+ required. Run as superuser on initial setup.
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE user_role AS ENUM ('owner', 'admin', 'reviewer', 'viewer', 'read_only');
CREATE TYPE interface_mode AS ENUM ('simple', 'professional', 'enterprise');
CREATE TYPE audit_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETE', 'PARTIAL', 'FAILED', 'CANCELLED');
CREATE TYPE verdict AS ENUM ('PASS', 'PARTIAL', 'FAIL', 'MISSING_EVIDENCE', 'NOT_APPLICABLE');
CREATE TYPE severity AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');
CREATE TYPE finding_status AS ENUM ('OPEN', 'IN_PROGRESS', 'EVIDENCE_SUBMITTED', 'VERIFYING', 'CLOSED', 'EXCEPTION', 'DISMISSED');
CREATE TYPE evidence_status AS ENUM ('UPLOADING', 'SCANNING', 'PROCESSING', 'EXTRACTING_TEXT', 'CLASSIFYING', 'READY', 'FAILED', 'REJECTED');
CREATE TYPE confidence_level AS ENUM ('HIGH', 'MEDIUM', 'LOW', 'MANUAL');
CREATE TYPE filing_status AS ENUM ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'SUBMITTED', 'ACCEPTED', 'REJECTED');
CREATE TYPE monitoring_event_type AS ENUM ('REGULATORY_CHANGE', 'ALERT', 'DEADLINE', 'OBLIGATION_DUE');
CREATE TYPE webhook_event AS ENUM (
  'audit.completed', 'audit.failed',
  'finding.created', 'finding.closed',
  'evidence.processed', 'evidence.failed',
  'remediation.status_changed', 'filing.submitted'
);

-- =============================================================================
-- TENANTS
-- =============================================================================

CREATE TABLE tenants (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name              TEXT NOT NULL,
  slug              TEXT NOT NULL UNIQUE,
  plan              TEXT NOT NULL DEFAULT 'trial' CHECK (plan IN ('trial', 'micro', 'starter', 'professional', 'enterprise')),
  plan_limits       JSONB NOT NULL DEFAULT '{"max_audits_per_month": 5, "max_entities": 1, "max_users": 3}',
  billing_email     TEXT,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  is_suspended      BOOLEAN NOT NULL DEFAULT FALSE,
  suspension_reason TEXT,
  trial_ends_at     TIMESTAMPTZ,
  metadata          JSONB NOT NULL DEFAULT '{}',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);

-- =============================================================================
-- USERS
-- =============================================================================

CREATE TABLE users (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  email             TEXT NOT NULL,
  full_name         TEXT NOT NULL,
  avatar_url        TEXT,
  role              user_role NOT NULL DEFAULT 'reviewer',
  interface_mode    interface_mode NOT NULL DEFAULT 'professional',
  preferred_language TEXT NOT NULL DEFAULT 'en',
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  email_verified    BOOLEAN NOT NULL DEFAULT FALSE,
  mfa_enabled       BOOLEAN NOT NULL DEFAULT FALSE,
  mfa_secret        TEXT,                               -- encrypted TOTP secret
  backup_codes      TEXT[],                             -- encrypted backup codes
  last_login_at     TIMESTAMPTZ,
  failed_login_count INTEGER NOT NULL DEFAULT 0,
  locked_until      TIMESTAMPTZ,
  password_hash     TEXT,                               -- bcrypt hash
  notification_prefs JSONB NOT NULL DEFAULT '{"email_audit_complete": true, "email_findings": true}',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, email)
);

CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- =============================================================================
-- ENTITIES (companies / AI systems being audited)
-- =============================================================================

CREATE TABLE entities (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  name              TEXT NOT NULL,
  description       TEXT,
  entity_type       TEXT NOT NULL DEFAULT 'company' CHECK (entity_type IN ('company', 'ai_system', 'department', 'product')),
  jurisdiction      TEXT NOT NULL,                      -- ISO 3166-1 alpha-2: 'GB', 'US', 'AE'
  industry_sector   TEXT,
  company_size      TEXT CHECK (company_size IN ('micro', 'small', 'medium', 'large', 'enterprise')),
  regulatory_regimes TEXT[] NOT NULL DEFAULT '{}',      -- ['AML', 'GDPR', 'FCA']
  metadata          JSONB NOT NULL DEFAULT '{}',
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_entities_tenant_id ON entities(tenant_id);
CREATE INDEX idx_entities_tenant_active ON entities(tenant_id, is_active);

-- =============================================================================
-- EVIDENCE ITEMS
-- =============================================================================

CREATE TABLE evidence_items (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  entity_id         UUID REFERENCES entities(id) ON DELETE CASCADE,
  audit_run_id      UUID,                               -- set after audit association (FK added below)
  filename          TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  mime_type         TEXT NOT NULL,
  file_size_bytes   BIGINT NOT NULL,
  file_hash         TEXT NOT NULL,                      -- SHA-256, immutable after upload
  storage_path      TEXT NOT NULL,                      -- object storage path
  status            evidence_status NOT NULL DEFAULT 'UPLOADING',
  category          TEXT,                               -- AML_POLICY, TRAINING_RECORDS, etc.
  category_confidence confidence_level,
  extracted_text    TEXT,                               -- full text from extraction
  extraction_method TEXT CHECK (extraction_method IN ('pdfplumber', 'docx', 'ocr', 'csv', 'json', 'manual')),
  ocr_confidence    NUMERIC(4, 3),                      -- 0.000 – 1.000
  page_count        INTEGER,
  word_count        INTEGER,
  is_password_protected BOOLEAN NOT NULL DEFAULT FALSE,
  virus_scan_result TEXT CHECK (virus_scan_result IN ('CLEAN', 'INFECTED', 'ERROR', 'SKIPPED')),
  processing_error  TEXT,
  supersedes_id     UUID REFERENCES evidence_items(id) ON DELETE SET NULL,
  uploaded_by       UUID REFERENCES users(id) ON DELETE SET NULL,
  metadata          JSONB NOT NULL DEFAULT '{}',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- file_hash is immutable after upload — enforce via trigger
CREATE OR REPLACE FUNCTION prevent_file_hash_change()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.file_hash IS NOT NULL AND NEW.file_hash != OLD.file_hash THEN
    RAISE EXCEPTION 'evidence file_hash is immutable after upload';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER evidence_hash_immutable
  BEFORE UPDATE ON evidence_items
  FOR EACH ROW EXECUTE FUNCTION prevent_file_hash_change();

CREATE INDEX idx_evidence_tenant_id ON evidence_items(tenant_id);
CREATE INDEX idx_evidence_entity_id ON evidence_items(entity_id);
CREATE INDEX idx_evidence_audit_run_id ON evidence_items(audit_run_id);
CREATE INDEX idx_evidence_status ON evidence_items(status);
CREATE INDEX idx_evidence_category ON evidence_items(category);
CREATE INDEX idx_evidence_file_hash ON evidence_items(file_hash);

-- =============================================================================
-- AUDIT RUNS
-- =============================================================================

CREATE TABLE audit_runs (
  id                TEXT PRIMARY KEY,                   -- format: TEN-YYYYMMDD-xxxxxxxx
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  entity_id         UUID REFERENCES entities(id) ON DELETE SET NULL,
  status            audit_status NOT NULL DEFAULT 'PENDING',
  jurisdiction      TEXT NOT NULL,
  regime_scope      TEXT[] NOT NULL DEFAULT '{}',       -- ['AML', 'GDPR']
  company_profile   JSONB NOT NULL DEFAULT '{}',
  evidence_ids      UUID[] NOT NULL DEFAULT '{}',
  overall_verdict   verdict,
  posture           TEXT CHECK (posture IN ('GREEN', 'AMBER', 'RED')),
  control_count     INTEGER NOT NULL DEFAULT 0,
  pass_count        INTEGER NOT NULL DEFAULT 0,
  partial_count     INTEGER NOT NULL DEFAULT 0,
  fail_count        INTEGER NOT NULL DEFAULT 0,
  missing_count     INTEGER NOT NULL DEFAULT 0,
  na_count          INTEGER NOT NULL DEFAULT 0,
  started_by        UUID REFERENCES users(id) ON DELETE SET NULL,
  started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at      TIMESTAMPTZ,
  duration_seconds  INTEGER,
  gold_case_version TEXT,
  model_version     TEXT NOT NULL DEFAULT 'claude-sonnet-4-6',
  error_message     TEXT,
  raw_output        JSONB,                              -- full engine output (large)
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add FK from evidence_items to audit_runs (now that audit_runs exists)
ALTER TABLE evidence_items
  ADD CONSTRAINT fk_evidence_audit_run
  FOREIGN KEY (audit_run_id) REFERENCES audit_runs(id) ON DELETE SET NULL;

CREATE INDEX idx_audit_runs_tenant_id ON audit_runs(tenant_id);
CREATE INDEX idx_audit_runs_entity_id ON audit_runs(entity_id);
CREATE INDEX idx_audit_runs_status ON audit_runs(status);
CREATE INDEX idx_audit_runs_tenant_status ON audit_runs(tenant_id, status);
CREATE INDEX idx_audit_runs_started_at ON audit_runs(started_at DESC);

-- =============================================================================
-- CONTROL VERDICTS (one row per control evaluated per audit run)
-- =============================================================================

CREATE TABLE control_verdicts (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  audit_run_id      TEXT NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
  control_id        TEXT NOT NULL,                      -- 'AML-04', 'GDPR-12', etc.
  control_name      TEXT NOT NULL,
  regime            TEXT NOT NULL,                      -- 'AML', 'GDPR'
  jurisdiction      TEXT NOT NULL,
  verdict           verdict NOT NULL,
  severity          severity NOT NULL DEFAULT 'MEDIUM',
  reason_code       TEXT NOT NULL,                      -- 'POLICY_NOT_FOUND', 'PARTIAL_COVERAGE'
  finding           TEXT,                               -- human-readable gap description
  requirement       TEXT,                               -- what the control requires
  gap               TEXT,                               -- specific gap identified
  risk              TEXT,                               -- risk if gap not addressed
  recommended_action TEXT,
  regulatory_reference TEXT,                            -- 'MLR 2017, Reg 28(1)'
  evidence_ids      UUID[] NOT NULL DEFAULT '{}',       -- which evidence was evaluated
  model_call_id     UUID,                               -- FK added below
  evaluated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (verdict IN ('PASS', 'PARTIAL', 'FAIL', 'MISSING_EVIDENCE', 'NOT_APPLICABLE'))
);

CREATE INDEX idx_control_verdicts_tenant_id ON control_verdicts(tenant_id);
CREATE INDEX idx_control_verdicts_audit_run_id ON control_verdicts(audit_run_id);
CREATE INDEX idx_control_verdicts_verdict ON control_verdicts(verdict);
CREATE INDEX idx_control_verdicts_regime ON control_verdicts(regime);
CREATE INDEX idx_control_verdicts_tenant_verdict ON control_verdicts(tenant_id, verdict);

-- =============================================================================
-- FINDINGS (derived from control_verdicts — the actionable items)
-- =============================================================================

CREATE TABLE findings (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  entity_id         UUID REFERENCES entities(id) ON DELETE SET NULL,
  audit_run_id      TEXT NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
  control_verdict_id UUID REFERENCES control_verdicts(id) ON DELETE SET NULL,
  control_id        TEXT NOT NULL,
  control_name      TEXT NOT NULL,
  regime            TEXT NOT NULL,
  jurisdiction      TEXT NOT NULL,
  verdict           verdict NOT NULL,
  severity          severity NOT NULL,
  status            finding_status NOT NULL DEFAULT 'OPEN',
  finding           TEXT NOT NULL,
  requirement       TEXT,
  gap               TEXT,
  risk              TEXT,
  recommended_action TEXT,
  regulatory_reference TEXT,
  assigned_to       UUID REFERENCES users(id) ON DELETE SET NULL,
  due_date          DATE,
  closed_at         TIMESTAMPTZ,
  closed_by         UUID REFERENCES users(id) ON DELETE SET NULL,
  exception_reason  TEXT,                               -- if status = EXCEPTION
  notes             TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_findings_tenant_id ON findings(tenant_id);
CREATE INDEX idx_findings_audit_run_id ON findings(audit_run_id);
CREATE INDEX idx_findings_entity_id ON findings(entity_id);
CREATE INDEX idx_findings_status ON findings(status);
CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_assigned_to ON findings(assigned_to);
CREATE INDEX idx_findings_tenant_status ON findings(tenant_id, status);
CREATE INDEX idx_findings_tenant_severity ON findings(tenant_id, severity);
-- Composite for dashboard queries
CREATE INDEX idx_findings_tenant_status_severity ON findings(tenant_id, status, severity);

-- =============================================================================
-- FINDINGS ACTIVITY (immutable timeline — no UPDATE/DELETE)
-- =============================================================================

CREATE TABLE findings_activity (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  finding_id        UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
  actor_type        TEXT NOT NULL CHECK (actor_type IN ('user', 'system')),
  actor_id          UUID REFERENCES users(id) ON DELETE SET NULL,
  action            TEXT NOT NULL,                      -- 'STATUS_CHANGED', 'ASSIGNED', 'NOTE_ADDED'
  from_status       finding_status,
  to_status         finding_status,
  note              TEXT,
  metadata          JSONB NOT NULL DEFAULT '{}',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Immutability: no UPDATE or DELETE on findings_activity
CREATE OR REPLACE FUNCTION prevent_findings_activity_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'findings_activity is immutable — no updates or deletes permitted';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER findings_activity_immutable_update
  BEFORE UPDATE ON findings_activity
  FOR EACH ROW EXECUTE FUNCTION prevent_findings_activity_mutation();

CREATE TRIGGER findings_activity_immutable_delete
  BEFORE DELETE ON findings_activity
  FOR EACH ROW EXECUTE FUNCTION prevent_findings_activity_mutation();

CREATE INDEX idx_findings_activity_finding_id ON findings_activity(finding_id);
CREATE INDEX idx_findings_activity_tenant_id ON findings_activity(tenant_id);

-- =============================================================================
-- REMEDIATION ITEMS
-- =============================================================================

CREATE TABLE remediation_items (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  finding_id        UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
  audit_run_id      TEXT REFERENCES audit_runs(id) ON DELETE SET NULL,
  title             TEXT NOT NULL,
  description       TEXT,
  status            finding_status NOT NULL DEFAULT 'OPEN',
  priority          severity NOT NULL DEFAULT 'MEDIUM',
  assigned_to       UUID REFERENCES users(id) ON DELETE SET NULL,
  due_date          DATE,
  evidence_submitted_path TEXT,                         -- storage path for remediation evidence
  verification_audit_run_id TEXT REFERENCES audit_runs(id) ON DELETE SET NULL,
  closed_at         TIMESTAMPTZ,
  closed_by         UUID REFERENCES users(id) ON DELETE SET NULL,
  created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_remediation_tenant_id ON remediation_items(tenant_id);
CREATE INDEX idx_remediation_finding_id ON remediation_items(finding_id);
CREATE INDEX idx_remediation_assigned_to ON remediation_items(assigned_to);
CREATE INDEX idx_remediation_status ON remediation_items(status);
CREATE INDEX idx_remediation_tenant_status ON remediation_items(tenant_id, status);
CREATE INDEX idx_remediation_due_date ON remediation_items(due_date);

-- =============================================================================
-- REMEDIATION ACTIVITY (immutable timeline)
-- =============================================================================

CREATE TABLE remediation_activity (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  remediation_id    UUID NOT NULL REFERENCES remediation_items(id) ON DELETE CASCADE,
  actor_type        TEXT NOT NULL CHECK (actor_type IN ('user', 'system')),
  actor_id          UUID REFERENCES users(id) ON DELETE SET NULL,
  action            TEXT NOT NULL,
  from_status       finding_status,
  to_status         finding_status,
  note              TEXT NOT NULL,
  metadata          JSONB NOT NULL DEFAULT '{}',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER remediation_activity_immutable_update
  BEFORE UPDATE ON remediation_activity
  FOR EACH ROW EXECUTE FUNCTION prevent_findings_activity_mutation();

CREATE TRIGGER remediation_activity_immutable_delete
  BEFORE DELETE ON remediation_activity
  FOR EACH ROW EXECUTE FUNCTION prevent_findings_activity_mutation();

CREATE INDEX idx_remediation_activity_remediation_id ON remediation_activity(remediation_id);
CREATE INDEX idx_remediation_activity_tenant_id ON remediation_activity(tenant_id);

-- =============================================================================
-- MODEL CALLS (every AI model invocation logged — Bible Rule 6)
-- =============================================================================

CREATE TABLE model_calls (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID REFERENCES tenants(id) ON DELETE SET NULL,
  audit_run_id      TEXT REFERENCES audit_runs(id) ON DELETE SET NULL,
  control_id        TEXT,
  call_type         TEXT NOT NULL,                      -- 'classification', 'explanation', 'narrative', 'extraction'
  model             TEXT NOT NULL,                      -- 'claude-sonnet-4-6'
  prompt_tokens     INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  total_tokens      INTEGER NOT NULL DEFAULT 0,
  latency_ms        INTEGER,
  timed_out         BOOLEAN NOT NULL DEFAULT FALSE,
  error             TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add FK from control_verdicts to model_calls
ALTER TABLE control_verdicts
  ADD CONSTRAINT fk_control_verdict_model_call
  FOREIGN KEY (model_call_id) REFERENCES model_calls(id) ON DELETE SET NULL;

CREATE INDEX idx_model_calls_tenant_id ON model_calls(tenant_id);
CREATE INDEX idx_model_calls_audit_run_id ON model_calls(audit_run_id);
CREATE INDEX idx_model_calls_created_at ON model_calls(created_at DESC);

-- =============================================================================
-- AUDIT LOG (immutable — Bible Rule 3: INSERT only, no UPDATE or DELETE ever)
-- =============================================================================

CREATE TABLE audit_log (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID REFERENCES tenants(id) ON DELETE SET NULL,
  user_id           UUID REFERENCES users(id) ON DELETE SET NULL,
  action            TEXT NOT NULL,                      -- 'AUDIT_STARTED', 'FINDING_CLOSED', etc.
  resource_type     TEXT NOT NULL,                      -- 'audit_run', 'finding', 'evidence_item'
  resource_id       TEXT,                               -- string ID of affected resource
  ip_address        INET,
  user_agent        TEXT,
  request_id        TEXT,
  changes           JSONB,                              -- before/after for mutations
  metadata          JSONB NOT NULL DEFAULT '{}',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enforce immutability
CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is immutable — no updates or deletes permitted (Bible Rule 3)';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_immutable_update
  BEFORE UPDATE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();

CREATE TRIGGER audit_log_immutable_delete
  BEFORE DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();

CREATE INDEX idx_audit_log_tenant_id ON audit_log(tenant_id);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);

-- =============================================================================
-- API KEYS
-- =============================================================================

CREATE TABLE api_keys (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
  name              TEXT NOT NULL,                      -- human label: "CI/CD Integration"
  key_prefix        TEXT NOT NULL,                      -- first 8 chars for display: "tnk_live"
  key_hash          TEXT NOT NULL UNIQUE,               -- SHA-256 of the full key
  scopes            TEXT[] NOT NULL DEFAULT '{}',       -- ['audits:read', 'evidence:write']
  last_used_at      TIMESTAMPTZ,
  expires_at        TIMESTAMPTZ,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_tenant_id ON api_keys(tenant_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);

-- =============================================================================
-- WEBHOOK ENDPOINTS
-- =============================================================================

CREATE TABLE webhook_endpoints (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  url               TEXT NOT NULL,
  events            webhook_event[] NOT NULL DEFAULT '{}',
  secret            TEXT NOT NULL,                      -- HMAC signing secret (encrypted at rest)
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  failure_count     INTEGER NOT NULL DEFAULT 0,
  last_success_at   TIMESTAMPTZ,
  last_failure_at   TIMESTAMPTZ,
  created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_webhooks_tenant_id ON webhook_endpoints(tenant_id);

CREATE TABLE webhook_deliveries (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  endpoint_id       UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
  event_type        webhook_event NOT NULL,
  payload           JSONB NOT NULL,
  http_status       INTEGER,
  response_body     TEXT,
  duration_ms       INTEGER,
  success           BOOLEAN,
  attempt_number    INTEGER NOT NULL DEFAULT 1,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_webhook_deliveries_endpoint_id ON webhook_deliveries(endpoint_id);
CREATE INDEX idx_webhook_deliveries_tenant_id ON webhook_deliveries(tenant_id);

-- =============================================================================
-- REGULATORY ALERTS
-- =============================================================================

CREATE TABLE regulatory_alerts (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  title             TEXT NOT NULL,
  summary           TEXT NOT NULL,
  jurisdiction      TEXT NOT NULL,
  regime            TEXT,
  severity          severity NOT NULL DEFAULT 'MEDIUM',
  source_url        TEXT,
  effective_date    DATE,
  is_read           BOOLEAN NOT NULL DEFAULT FALSE,
  read_by           UUID REFERENCES users(id) ON DELETE SET NULL,
  read_at           TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_regulatory_alerts_tenant_id ON regulatory_alerts(tenant_id);
CREATE INDEX idx_regulatory_alerts_tenant_unread ON regulatory_alerts(tenant_id, is_read);

-- =============================================================================
-- MONITORING CONFIG & EVENTS
-- =============================================================================

CREATE TABLE monitoring_config (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE UNIQUE,
  enabled           BOOLEAN NOT NULL DEFAULT FALSE,
  jurisdictions     TEXT[] NOT NULL DEFAULT '{}',
  regimes           TEXT[] NOT NULL DEFAULT '{}',
  alert_email       TEXT,
  alert_slack_webhook TEXT,
  check_frequency_hours INTEGER NOT NULL DEFAULT 24,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE monitoring_events (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  event_type        monitoring_event_type NOT NULL,
  title             TEXT NOT NULL,
  description       TEXT,
  jurisdiction      TEXT,
  regime            TEXT,
  severity          severity NOT NULL DEFAULT 'MEDIUM',
  source            TEXT,
  action_required   BOOLEAN NOT NULL DEFAULT FALSE,
  deadline          DATE,
  metadata          JSONB NOT NULL DEFAULT '{}',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_monitoring_events_tenant_id ON monitoring_events(tenant_id);
CREATE INDEX idx_monitoring_events_created_at ON monitoring_events(created_at DESC);

-- =============================================================================
-- COMPLIANCE OBLIGATIONS
-- =============================================================================

CREATE TABLE compliance_obligations (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  entity_id         UUID REFERENCES entities(id) ON DELETE CASCADE,
  title             TEXT NOT NULL,
  description       TEXT,
  jurisdiction      TEXT NOT NULL,
  regime            TEXT NOT NULL,
  obligation_type   TEXT NOT NULL,                      -- 'filing', 'audit', 'training', 'review'
  frequency         TEXT,                               -- 'annual', 'quarterly', 'monthly', 'ad_hoc'
  next_due_date     DATE,
  last_completed_at TIMESTAMPTZ,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  metadata          JSONB NOT NULL DEFAULT '{}',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_obligations_tenant_id ON compliance_obligations(tenant_id);
CREATE INDEX idx_obligations_next_due ON compliance_obligations(next_due_date);

-- =============================================================================
-- FILING SUBMISSIONS (Bible Rule 9: always requires explicit human approval)
-- =============================================================================

CREATE TABLE filing_submissions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  entity_id         UUID REFERENCES entities(id) ON DELETE SET NULL,
  obligation_id     UUID REFERENCES compliance_obligations(id) ON DELETE SET NULL,
  filing_type       TEXT NOT NULL,
  jurisdiction      TEXT NOT NULL,
  regulator         TEXT NOT NULL,
  title             TEXT NOT NULL,
  reference_number  TEXT,
  status            filing_status NOT NULL DEFAULT 'DRAFT',
  form_data         JSONB NOT NULL DEFAULT '{}',
  submitted_at      TIMESTAMPTZ,
  submitted_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  approval_name     TEXT,                               -- typed name confirmation (Bible Rule 9)
  approval_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
  regulator_response JSONB,
  due_date          DATE,
  period_start      DATE,
  period_end        DATE,
  created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_filings_tenant_id ON filing_submissions(tenant_id);
CREATE INDEX idx_filings_status ON filing_submissions(status);
CREATE INDEX idx_filings_due_date ON filing_submissions(due_date);

-- =============================================================================
-- FINANCE AUDIT RUNS
-- =============================================================================

CREATE TABLE finance_audit_runs (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  entity_id         UUID REFERENCES entities(id) ON DELETE SET NULL,
  title             TEXT NOT NULL,
  period_start      DATE NOT NULL,
  period_end        DATE NOT NULL,
  jurisdiction      TEXT NOT NULL,
  status            audit_status NOT NULL DEFAULT 'PENDING',
  control_count     INTEGER NOT NULL DEFAULT 0,
  pass_count        INTEGER NOT NULL DEFAULT 0,
  fail_count        INTEGER NOT NULL DEFAULT 0,
  material_weakness_count INTEGER NOT NULL DEFAULT 0,
  started_by        UUID REFERENCES users(id) ON DELETE SET NULL,
  completed_at      TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_finance_audit_runs_tenant_id ON finance_audit_runs(tenant_id);

CREATE TABLE finance_findings (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  finance_audit_id  UUID NOT NULL REFERENCES finance_audit_runs(id) ON DELETE CASCADE,
  control_id        TEXT NOT NULL,
  control_name      TEXT NOT NULL,
  finding           TEXT NOT NULL,
  severity          severity NOT NULL,
  is_material_weakness BOOLEAN NOT NULL DEFAULT FALSE,
  status            finding_status NOT NULL DEFAULT 'OPEN',
  assigned_to       UUID REFERENCES users(id) ON DELETE SET NULL,
  due_date          DATE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_finance_findings_tenant_id ON finance_findings(tenant_id);
CREATE INDEX idx_finance_findings_audit_id ON finance_findings(finance_audit_id);

-- =============================================================================
-- SIMPLE MODE WIZARD SESSIONS
-- =============================================================================

CREATE TABLE simple_mode_wizard_sessions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  step              INTEGER NOT NULL DEFAULT 1,
  answers           JSONB NOT NULL DEFAULT '{}',
  obligations       JSONB,
  completed         BOOLEAN NOT NULL DEFAULT FALSE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wizard_tenant_user ON simple_mode_wizard_sessions(tenant_id, user_id);

-- =============================================================================
-- GENERATED DOCUMENTS
-- =============================================================================

CREATE TABLE generated_documents (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  entity_id         UUID REFERENCES entities(id) ON DELETE SET NULL,
  document_type     TEXT NOT NULL,                      -- 'AML_POLICY', 'PRIVACY_NOTICE', 'RISK_ASSESSMENT'
  document_name     TEXT NOT NULL,
  generated_for     TEXT NOT NULL,                      -- regime or context
  language          TEXT NOT NULL DEFAULT 'en',
  storage_path      TEXT NOT NULL,
  is_draft          BOOLEAN NOT NULL DEFAULT TRUE,
  approved_by       UUID REFERENCES users(id) ON DELETE SET NULL,
  approved_at       TIMESTAMPTZ,
  supersedes_id     UUID REFERENCES generated_documents(id) ON DELETE SET NULL,
  generated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_generated_documents_tenant_id ON generated_documents(tenant_id);
CREATE INDEX idx_generated_documents_entity_id ON generated_documents(entity_id);

-- =============================================================================
-- UPLOAD SESSIONS (for chunked/multipart evidence uploads)
-- =============================================================================

CREATE TABLE upload_sessions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  entity_id         UUID REFERENCES entities(id) ON DELETE SET NULL,
  audit_run_id      TEXT REFERENCES audit_runs(id) ON DELETE SET NULL,
  filename          TEXT NOT NULL,
  mime_type         TEXT NOT NULL,
  file_size_bytes   BIGINT,
  status            TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'uploading', 'finalizing', 'complete', 'failed', 'cancelled')),
  storage_upload_id TEXT,                               -- S3/Supabase multipart upload ID
  storage_path      TEXT,
  evidence_item_id  UUID REFERENCES evidence_items(id) ON DELETE SET NULL,
  created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
  expires_at        TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '1 hour',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_upload_sessions_tenant_id ON upload_sessions(tenant_id);
CREATE INDEX idx_upload_sessions_status ON upload_sessions(status);

-- =============================================================================
-- DASHBOARD CACHE (pre-computed metrics — updated by background jobs)
-- =============================================================================

CREATE TABLE dashboard_cache (
  tenant_id         UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
  open_findings     INTEGER NOT NULL DEFAULT 0,
  critical_findings INTEGER NOT NULL DEFAULT 0,
  high_findings     INTEGER NOT NULL DEFAULT 0,
  controls_passing  INTEGER NOT NULL DEFAULT 0,
  controls_total    INTEGER NOT NULL DEFAULT 0,
  last_audit_at     TIMESTAMPTZ,
  last_audit_posture TEXT,
  regime_health     JSONB NOT NULL DEFAULT '{}',       -- per-regime pass/fail/partial counts
  recent_activity   JSONB NOT NULL DEFAULT '[]',       -- last 10 events
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- UPDATED_AT TRIGGER (auto-update updated_at on mutations)
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOR tbl IN SELECT unnest(ARRAY[
    'tenants', 'users', 'entities', 'evidence_items', 'audit_runs',
    'findings', 'remediation_items', 'webhook_endpoints',
    'monitoring_config', 'compliance_obligations', 'filing_submissions',
    'finance_audit_runs', 'finance_findings', 'simple_mode_wizard_sessions',
    'upload_sessions'
  ]) LOOP
    EXECUTE format(
      'CREATE TRIGGER trg_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION update_updated_at()',
      tbl
    );
  END LOOP;
END;
$$;

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) — Bible Rule 4: tenant data never crosses boundaries
-- =============================================================================

ALTER TABLE tenants              ENABLE ROW LEVEL SECURITY;
ALTER TABLE users                ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities             ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_items       ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_runs           ENABLE ROW LEVEL SECURITY;
ALTER TABLE control_verdicts     ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings             ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings_activity    ENABLE ROW LEVEL SECURITY;
ALTER TABLE remediation_items    ENABLE ROW LEVEL SECURITY;
ALTER TABLE remediation_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_calls          ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log            ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys             ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_endpoints    ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_deliveries   ENABLE ROW LEVEL SECURITY;
ALTER TABLE regulatory_alerts    ENABLE ROW LEVEL SECURITY;
ALTER TABLE monitoring_config    ENABLE ROW LEVEL SECURITY;
ALTER TABLE monitoring_events    ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_obligations ENABLE ROW LEVEL SECURITY;
ALTER TABLE filing_submissions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE finance_audit_runs   ENABLE ROW LEVEL SECURITY;
ALTER TABLE finance_findings     ENABLE ROW LEVEL SECURITY;
ALTER TABLE simple_mode_wizard_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_documents  ENABLE ROW LEVEL SECURITY;
ALTER TABLE upload_sessions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_cache      ENABLE ROW LEVEL SECURITY;

-- Create the app role that the API uses
DO $$ BEGIN
  CREATE ROLE tenet_app NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Grant table access to app role
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO tenet_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO tenet_app;

-- RLS policies: app role can only see rows for the tenant in the current session variable
-- The application sets: SET LOCAL app.current_tenant_id = '<uuid>';

CREATE POLICY tenant_isolation ON tenants
  FOR ALL TO tenet_app
  USING (id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON users
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON entities
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON evidence_items
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON audit_runs
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON control_verdicts
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON findings
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON findings_activity
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON remediation_items
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON remediation_activity
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON model_calls
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

-- Audit log: INSERT allowed to all app users; SELECT scoped to tenant
CREATE POLICY audit_log_insert ON audit_log
  FOR INSERT TO tenet_app WITH CHECK (TRUE);

CREATE POLICY audit_log_select ON audit_log
  FOR SELECT TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON api_keys
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON webhook_endpoints
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON webhook_deliveries
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON regulatory_alerts
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON monitoring_config
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON monitoring_events
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON compliance_obligations
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON filing_submissions
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON finance_audit_runs
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON finance_findings
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON simple_mode_wizard_sessions
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON generated_documents
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON upload_sessions
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation ON dashboard_cache
  FOR ALL TO tenet_app
  USING (tenant_id::TEXT = current_setting('app.current_tenant_id', TRUE));

-- =============================================================================
-- AUDIT LOG REVOKE DELETE/UPDATE (Bible Rule 3 — belt and suspenders)
-- =============================================================================

REVOKE UPDATE, DELETE ON audit_log FROM tenet_app;
REVOKE UPDATE, DELETE ON findings_activity FROM tenet_app;
REVOKE UPDATE, DELETE ON remediation_activity FROM tenet_app;

-- =============================================================================
-- SEED: default tenant for development
-- =============================================================================

INSERT INTO tenants (id, name, slug, plan) VALUES
  ('00000000-0000-0000-0000-000000000001', 'Tenet Demo', 'tenet-demo', 'professional')
ON CONFLICT DO NOTHING;
