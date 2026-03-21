"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { createAudit } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import type { CreateAuditRequest } from "@/lib/types";
import { cn } from "@/lib/utils";

const EMPTY: CreateAuditRequest = {
  audit_kind: "",
  entity_id: "",
  system_name: "",
  jurisdiction: "",
  framework: "",
  scheduled_date: null,
  note: null,
};

const SELECT_CLASS = cn(
  "w-full h-9 px-3 rounded-base border border-neutral-200 bg-white",
  "text-14 text-neutral-800",
  "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500",
  "hover:border-neutral-300 transition-colors duration-base",
);

const TEXTAREA_CLASS = cn(
  "w-full px-3 py-2 rounded-base border border-neutral-200 bg-white",
  "text-14 text-neutral-800 placeholder:text-neutral-400",
  "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500",
  "hover:border-neutral-300 transition-colors duration-base resize-none",
);

const FIELD_LABEL = "block text-13 font-medium text-neutral-600 mb-1.5";

interface Entity {
  id: string;
  name: string;
  entity_type: string;
  jurisdiction: string;
}

async function fetchEntities(userId: string): Promise<Entity[]> {
  const token = typeof window !== "undefined" ? sessionStorage.getItem("tenet:access_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token && !token.startsWith("dev:")) {
    headers["Authorization"] = `Bearer ${token}`;
  } else {
    headers["X-User-ID"] = userId;
  }
  try {
    const res = await fetch("/api/proxy/v1/entities?limit=50", { headers });
    const json = await res.json();
    return json?.data?.items ?? json?.data ?? [];
  } catch {
    return [];
  }
}

export default function NewAuditPage() {
  const { userId } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState<CreateAuditRequest>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [entitiesLoaded, setEntitiesLoaded] = useState(false);

  useEffect(() => {
    if (!userId) return;
    fetchEntities(userId).then((list) => {
      setEntities(list);
      setEntitiesLoaded(true);
      // Auto-fill entity_id if only one entity
      if (list.length === 1) {
        setForm((f) => ({ ...f, entity_id: list[0].id }));
      }
    });
  }, [userId]);

  function field(key: keyof CreateAuditRequest) {
    return (
      e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
    ) => {
      setForm((f) => ({ ...f, [key]: e.target.value || null }));
      setError(null);
    };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.system_name || !form.jurisdiction || !form.framework) {
      setError("System name, jurisdiction, and framework are required.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // Use first entity if none selected, or allow empty
      const entityId = form.entity_id || (entities[0]?.id ?? null);
      const audit = await createAudit(userId!, {
        ...form,
        audit_kind: form.audit_kind || "compliance_audit",
        entity_id: entityId,
        system_name: form.system_name!,
        jurisdiction: form.jurisdiction!,
        framework: form.framework!,
      });
      router.push(`/audits/${audit.audit_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create audit.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="New Audit"
        subtitle="Register a new compliance audit for an AI system or business unit."
        breadcrumbs={[{ label: "Audits", href: "/audits" }, { label: "New" }]}
      />

      <Card className="max-w-[480px]">
        <form onSubmit={handleSubmit} className="space-y-5">
          <Input
            label="System Name"
            placeholder="e.g. Transaction Screening Engine"
            value={form.system_name ?? ""}
            onChange={field("system_name")}
            required
          />

          {/* Entity selector */}
          <div>
            <label className={FIELD_LABEL}>Entity</label>
            {!entitiesLoaded ? (
              <div className="h-9 bg-neutral-100 rounded-base animate-pulse" />
            ) : entities.length > 0 ? (
              <select
                className={SELECT_CLASS}
                value={form.entity_id ?? ""}
                onChange={field("entity_id")}
              >
                <option value="">Select entity…</option>
                {entities.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name} ({e.entity_type})
                  </option>
                ))}
              </select>
            ) : (
              <Input
                label=""
                placeholder="Entity ID (create one via Onboarding first)"
                value={form.entity_id ?? ""}
                onChange={field("entity_id")}
              />
            )}
          </div>

          <div>
            <label className={FIELD_LABEL}>
              Audit Kind
            </label>
            <select
              className={SELECT_CLASS}
              value={form.audit_kind ?? ""}
              onChange={field("audit_kind")}
            >
              <option value="">Select… (optional)</option>
              <option value="aml_periodic">AML Periodic</option>
              <option value="kyc_periodic">KYC Periodic</option>
              <option value="sanctions_screening">Sanctions Screening</option>
              <option value="governance_review">Governance Review</option>
              <option value="vendor_risk">Vendor Risk</option>
              <option value="fraud_controls">Fraud Controls</option>
              <option value="gdpr_review">GDPR Review</option>
              <option value="compliance_audit">General Compliance Audit</option>
            </select>
          </div>

          <div>
            <label className={FIELD_LABEL}>
              Framework <span className="text-danger-base ml-0.5">*</span>
            </label>
            <select
              className={SELECT_CLASS}
              value={form.framework ?? ""}
              onChange={field("framework")}
              required
            >
              <option value="">Select framework…</option>
              <option value="FCA">FCA (UK Financial Conduct Authority)</option>
              <option value="MAS">MAS (Monetary Authority of Singapore)</option>
              <option value="DFSA">DFSA (Dubai Financial Services Authority)</option>
              <option value="SEC">SEC (US Securities and Exchange Commission)</option>
              <option value="FINCEN">FinCEN (US Financial Crimes Enforcement)</option>
              <option value="GDPR">GDPR (EU General Data Protection Regulation)</option>
              <option value="AML">AML (Anti-Money Laundering)</option>
              <option value="AUSTRAC">AUSTRAC (Australia)</option>
              <option value="FINTRAC">FINTRAC (Canada)</option>
            </select>
          </div>

          <div>
            <label className={FIELD_LABEL}>
              Jurisdiction <span className="text-danger-base ml-0.5">*</span>
            </label>
            <select
              className={SELECT_CLASS}
              value={form.jurisdiction ?? ""}
              onChange={field("jurisdiction")}
              required
            >
              <option value="">Select jurisdiction…</option>
              <option value="GB">United Kingdom (GB)</option>
              <option value="EU">European Union (EU)</option>
              <option value="US">United States (US)</option>
              <option value="SG">Singapore (SG)</option>
              <option value="AE">UAE / DIFC (AE)</option>
              <option value="AU">Australia (AU)</option>
              <option value="CA">Canada (CA)</option>
              <option value="HK">Hong Kong (HK)</option>
              <option value="IN">India (IN)</option>
            </select>
          </div>

          <div>
            <label className={FIELD_LABEL}>Note</label>
            <textarea
              rows={3}
              className={TEXTAREA_CLASS}
              placeholder="Optional context for this audit run."
              value={form.note ?? ""}
              onChange={field("note")}
            />
          </div>

          {error && (
            <p
              role="alert"
              className="text-14 text-danger-dark bg-danger-light border border-danger-base/20 rounded-base px-3 py-2"
            >
              {error}
            </p>
          )}

          <div className="flex items-center gap-3 pt-2">
            <Button type="submit" variant="primary" loading={loading}>
              Create Audit
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.push("/audits")}
            >
              Cancel
            </Button>
          </div>
        </form>
      </Card>
    </>
  );
}
