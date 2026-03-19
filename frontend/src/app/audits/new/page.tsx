"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { createAudit } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { CreateAuditRequest } from "@/lib/types";

const EMPTY: CreateAuditRequest = {
  audit_kind: "",
  entity_id: "",
  system_name: "",
  jurisdiction: "",
  framework: "",
  scheduled_date: null,
  note: null,
};

function FieldLabel({
  htmlFor,
  label,
  required,
}: {
  htmlFor: string;
  label: string;
  required?: boolean;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="block text-xs font-medium text-text-secondary uppercase tracking-wide mb-1.5"
    >
      {label}
      {required && <span className="ml-1 text-red-500">*</span>}
    </label>
  );
}

const INPUT =
  "w-full px-3 py-2 border border-surface-border rounded bg-surface text-text text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-fast";

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
            <div>
              <FieldLabel htmlFor="system_name" label="System Name" required />
              <input
                id="system_name"
                type="text"
                className={INPUT}
                placeholder="e.g. Transaction Screening Engine"
                value={form.system_name ?? ""}
                onChange={field("system_name")}
              />
            </div>
            <div>
              <FieldLabel htmlFor="entity_id" label="Entity ID" required />
              <input
                id="entity_id"
                type="text"
                className={INPUT}
                placeholder="e.g. entity_acme"
                value={form.entity_id ?? ""}
                onChange={field("entity_id")}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <FieldLabel htmlFor="audit_kind" label="Audit Kind" required />
              <select
                id="audit_kind"
                className={INPUT}
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
            <div>
              <FieldLabel htmlFor="framework" label="Framework" required />
              <input
                id="framework"
                type="text"
                className={INPUT}
                placeholder="e.g. FCA, FinCEN, MAS"
                value={form.framework ?? ""}
                onChange={field("framework")}
              />
            </div>
          </div>

          <div>
            <FieldLabel htmlFor="jurisdiction" label="Jurisdiction" required />
            <input
              id="jurisdiction"
              type="text"
              className={INPUT}
              placeholder="e.g. UK, US, SG"
              value={form.jurisdiction ?? ""}
              onChange={field("jurisdiction")}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <FieldLabel
                htmlFor="scheduled_date"
                label="Scheduled Date"
              />
              <input
                id="scheduled_date"
                type="date"
                className={INPUT}
                value={form.scheduled_date ?? ""}
                onChange={field("scheduled_date")}
              />
            </div>
          </div>

          <div>
            <FieldLabel htmlFor="note" label="Note" />
            <textarea
              id="note"
              rows={3}
              className={INPUT}
              placeholder="Optional note for this audit."
              value={form.note ?? ""}
              onChange={field("note")}
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
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
