"use client";

import { useState } from "react";
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

// Shared select/textarea styles matching the Input component
const SELECT_CLASS = cn(
  "w-full h-8 px-3 rounded-base border border-neutral-200 bg-white",
  "text-14 text-neutral-800 placeholder:text-neutral-400",
  "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500",
  "transition-colors duration-base",
);

const TEXTAREA_CLASS = cn(
  "w-full px-3 py-2 rounded-base border border-neutral-200 bg-white",
  "text-14 text-neutral-800 placeholder:text-neutral-400",
  "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500",
  "transition-colors duration-base resize-none",
);

const FIELD_LABEL = "block text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1.5";

export default function NewAuditPage() {
  const { userId } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState<CreateAuditRequest>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    if (
      !form.audit_kind ||
      !form.entity_id ||
      !form.system_name ||
      !form.jurisdiction ||
      !form.framework
    ) {
      setError("All required fields must be filled.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const audit = await createAudit(userId!, {
        ...form,
        audit_kind: form.audit_kind!,
        entity_id: form.entity_id!,
        system_name: form.system_name!,
        jurisdiction: form.jurisdiction!,
        framework: form.framework!,
      });
      router.push(`/audits/${audit.audit_id}`);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to create audit.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="New Audit"
        subtitle="Register a new compliance audit for a system."
        breadcrumbs={[{ label: "Audits", href: "/audits" }, { label: "New" }]}
      />

      <Card className="max-w-xl">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="System Name"
              placeholder="e.g. Transaction Screening Engine"
              value={form.system_name ?? ""}
              onChange={field("system_name")}
              required
            />
            <Input
              label="Entity ID"
              placeholder="e.g. entity_acme"
              value={form.entity_id ?? ""}
              onChange={field("entity_id")}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={FIELD_LABEL}>
                Audit Kind <span className="text-danger-base ml-0.5">*</span>
              </label>
              <select
                className={SELECT_CLASS}
                value={form.audit_kind ?? ""}
                onChange={field("audit_kind")}
              >
                <option value="">Select…</option>
                <option value="aml_periodic">AML Periodic</option>
                <option value="kyc_periodic">KYC Periodic</option>
                <option value="sanctions_screening">Sanctions Screening</option>
                <option value="governance_review">Governance Review</option>
                <option value="vendor_risk">Vendor Risk</option>
                <option value="fraud_controls">Fraud Controls</option>
              </select>
            </div>
            <Input
              label="Framework"
              placeholder="e.g. FCA, FinCEN, MAS"
              value={form.framework ?? ""}
              onChange={field("framework")}
              required
            />
          </div>

          <Input
            label="Jurisdiction"
            placeholder="e.g. UK, US, SG"
            value={form.jurisdiction ?? ""}
            onChange={field("jurisdiction")}
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Scheduled Date"
              type="date"
              value={form.scheduled_date ?? ""}
              onChange={field("scheduled_date")}
            />
          </div>

          <div>
            <label className={FIELD_LABEL}>Note</label>
            <textarea
              rows={3}
              className={TEXTAREA_CLASS}
              placeholder="Optional note for this audit."
              value={form.note ?? ""}
              onChange={field("note")}
            />
          </div>

          {error && (
            <p className="text-14 text-danger-dark bg-danger-light border border-danger-base/20 rounded-base px-3 py-2">
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
