-- =============================================================================
-- TENET MIGRATION 002 — Schema completeness update
-- Adds missing columns for full audit workflow, report generation, evidence.
-- Run once on the database before starting the application.
-- =============================================================================

-- ─── 1. Extend audit_status enum ─────────────────────────────────────────────
-- Add CREATED (for newly created audits before they start) and BLOCKED (critical fails)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'CREATED' AND enumtypid = 'audit_status'::regtype) THEN
    ALTER TYPE audit_status ADD VALUE 'CREATED';
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'BLOCKED' AND enumtypid = 'audit_status'::regtype) THEN
    ALTER TYPE audit_status ADD VALUE 'BLOCKED';
  END IF;
END $$;

-- ─── 2. Extend audit_runs ────────────────────────────────────────────────────
-- Add columns for system tracking, framework, deployment decision
ALTER TABLE audit_runs
  ADD COLUMN IF NOT EXISTS system_name TEXT DEFAULT 'Untitled System',
  ADD COLUMN IF NOT EXISTS audit_kind TEXT DEFAULT 'compliance_audit',
  ADD COLUMN IF NOT EXISTS framework TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS deployment_decision TEXT DEFAULT 'UNKNOWN',
  ADD COLUMN IF NOT EXISTS release_ready BOOLEAN NOT NULL DEFAULT FALSE;

-- note column might already exist - add if not
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'audit_runs' AND column_name = 'note'
  ) THEN
    ALTER TABLE audit_runs ADD COLUMN note TEXT;
  END IF;
END $$;

-- ─── 3. Fix evidence_items ───────────────────────────────────────────────────
-- Add original_name as alias for original_filename (code uses original_name)
ALTER TABLE evidence_items
  ADD COLUMN IF NOT EXISTS original_name TEXT;

-- Populate original_name from original_filename if exists
UPDATE evidence_items SET original_name = original_filename WHERE original_name IS NULL AND original_filename IS NOT NULL;

-- Add document_type alias for category (code uses both)
-- document_type already exists based on schema check, but let's add if missing
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'evidence_items' AND column_name = 'document_type'
  ) THEN
    ALTER TABLE evidence_items ADD COLUMN document_type TEXT;
  END IF;
END $$;

-- Sync document_type from category
UPDATE evidence_items SET document_type = category WHERE document_type IS NULL AND category IS NOT NULL;

-- ─── 4. Fix control_verdicts ─────────────────────────────────────────────────
-- Add gap_description / risk_description as aliases (reports query uses these names)
ALTER TABLE control_verdicts
  ADD COLUMN IF NOT EXISTS gap_description TEXT,
  ADD COLUMN IF NOT EXISTS risk_description TEXT;

-- Populate from existing gap/risk columns
UPDATE control_verdicts
SET gap_description = gap, risk_description = risk
WHERE gap_description IS NULL;

-- ─── 5. Fix generated_documents ──────────────────────────────────────────────
-- Add missing columns needed by reports.py
ALTER TABLE generated_documents
  ADD COLUMN IF NOT EXISTS audit_run_id TEXT REFERENCES audit_runs(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS format TEXT DEFAULT 'JSON',
  ADD COLUMN IF NOT EXISTS file_hash TEXT,
  ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- ─── 6. Regulatory alerts and obligations ────────────────────────────────────
-- monitoring.py needs these tables
CREATE TABLE IF NOT EXISTS regulatory_alerts (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  title             TEXT NOT NULL,
  body              TEXT,
  severity          TEXT NOT NULL DEFAULT 'MEDIUM' CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
  jurisdiction      TEXT,
  regime            TEXT,
  source            TEXT,
  source_url        TEXT,
  is_read           BOOLEAN NOT NULL DEFAULT FALSE,
  is_dismissed      BOOLEAN NOT NULL DEFAULT FALSE,
  published_at      TIMESTAMPTZ DEFAULT NOW(),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_regulatory_alerts_tenant ON regulatory_alerts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_regulatory_alerts_is_read ON regulatory_alerts(tenant_id, is_read);

CREATE TABLE IF NOT EXISTS compliance_obligations (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  title             TEXT NOT NULL,
  description       TEXT,
  jurisdiction      TEXT,
  regime            TEXT,
  status            TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'OVERDUE', 'WAIVED')),
  next_due_date     DATE,
  recurring         BOOLEAN NOT NULL DEFAULT FALSE,
  recurrence_period TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_compliance_obligations_tenant ON compliance_obligations(tenant_id);

-- Monitoring config
CREATE TABLE IF NOT EXISTS monitoring_config (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
  jurisdictions     TEXT[] NOT NULL DEFAULT '{}',
  regime_scope      TEXT[] NOT NULL DEFAULT '{}',
  alert_email       TEXT,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── 7. Remediation items ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS remediation_items (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  finding_id        UUID REFERENCES findings(id) ON DELETE SET NULL,
  audit_id          TEXT REFERENCES audit_runs(id) ON DELETE SET NULL,
  title             TEXT NOT NULL,
  gap_note          TEXT,
  status            TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'evidence_submitted', 'resolved', 'not_applicable')),
  release_blocking  BOOLEAN NOT NULL DEFAULT FALSE,
  assigned_to       UUID REFERENCES users(id) ON DELETE SET NULL,
  due_date          DATE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_remediation_tenant ON remediation_items(tenant_id);

-- ─── 8. Calendar events ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calendar_events (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  title             TEXT NOT NULL,
  description       TEXT,
  event_type        TEXT NOT NULL DEFAULT 'obligation',
  start_date        DATE NOT NULL,
  end_date          DATE,
  jurisdiction      TEXT,
  regime            TEXT,
  status            TEXT DEFAULT 'PENDING',
  related_id        TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_calendar_events_tenant ON calendar_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_start ON calendar_events(tenant_id, start_date);

-- ─── 9. Findings activity ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS findings_activity (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  finding_id        UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
  actor_type        TEXT NOT NULL DEFAULT 'user',
  actor_id          TEXT,
  action            TEXT NOT NULL,
  from_status       TEXT,
  to_status         TEXT,
  note              TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_findings_activity_finding ON findings_activity(finding_id);

-- ─── 10. API keys ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_keys (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name              TEXT NOT NULL,
  key_hash          TEXT NOT NULL UNIQUE,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  expires_at        TIMESTAMPTZ,
  last_used_at      TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── 11. Audit log ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID REFERENCES tenants(id) ON DELETE SET NULL,
  user_id           UUID REFERENCES users(id) ON DELETE SET NULL,
  action            TEXT NOT NULL,
  resource_type     TEXT,
  resource_id       TEXT,
  ip_address        INET,
  user_agent        TEXT,
  request_id        TEXT,
  changes           JSONB,
  metadata          JSONB NOT NULL DEFAULT '{}',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_tenant ON audit_log(tenant_id);

-- ─── 12. Model calls ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_calls (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID REFERENCES tenants(id) ON DELETE SET NULL,
  audit_run_id      TEXT REFERENCES audit_runs(id) ON DELETE SET NULL,
  control_id        TEXT,
  call_type         TEXT NOT NULL,
  model             TEXT NOT NULL,
  prompt_tokens     INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  total_tokens      INTEGER NOT NULL DEFAULT 0,
  latency_ms        INTEGER,
  timed_out         BOOLEAN NOT NULL DEFAULT FALSE,
  error             TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Done ────────────────────────────────────────────────────────────────────
