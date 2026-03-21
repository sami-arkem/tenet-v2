"use client";

import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { getEvidence, submitOcrText } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Button } from "@/components/ui/Button";
import { PageSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { formatDate, formatBytes } from "@/lib/utils";
import { useState } from "react";
import { ArrowLeft, CheckCircle2, XCircle } from "lucide-react";

function MetaRow({ label, value, mono = false }: { label: string; value: string | number | boolean | null | undefined; mono?: boolean }) {
  const display = value == null ? "—" : typeof value === "boolean" ? (value ? "Yes" : "No") : String(value);
  return (
    <div className="flex items-start py-2.5 border-b border-neutral-200 last:border-0 gap-4">
      <div className="w-48 flex-none text-12 text-neutral-400 uppercase tracking-wide">
        {label}
      </div>
      <div className={`text-14 text-neutral-800 ${mono ? "mono" : ""}`}>{display}</div>
    </div>
  );
}

function ReadinessIcon({ ready }: { ready: boolean }) {
  return ready ? (
    <CheckCircle2 size={14} className="text-success-base" />
  ) : (
    <XCircle size={14} className="text-danger-base" />
  );
}

export default function EvidenceDetailPage() {
  const { evidenceId } = useParams<{ evidenceId: string }>();
  const { userId } = useAuth();
  const router = useRouter();
  const [ocrText, setOcrText] = useState("");
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrResult, setOcrResult] = useState<string | null>(null);
  const [ocrError, setOcrError] = useState<string | null>(null);

  const {
    data: evidence,
    error,
    isLoading,
    mutate,
  } = useSWR(
    userId && evidenceId ? ["evidence-detail", evidenceId, userId] : null,
    ([, id, uid]) => getEvidence(uid, id),
    { refreshInterval: 10_000 },
  );

  async function handleOcrSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ocrText.trim()) return;
    setOcrLoading(true);
    setOcrError(null);
    setOcrResult(null);
    try {
      const res = await submitOcrText(userId!, evidenceId, ocrText);
      setOcrResult(res.message);
      await mutate();
    } catch (err: unknown) {
      setOcrError(err instanceof Error ? err.message : "Failed to submit OCR text.");
    } finally {
      setOcrLoading(false);
    }
  }

  if (isLoading) return <PageSkeleton />;
  if (error)
    return <ErrorMessage message={error.message} onRetry={() => mutate()} />;
  if (!evidence) return null;

  const canSubmitOcr =
    evidence.status !== "READY" && evidence.status !== "CANCELLED";

  return (
    <>
      <PageHeader
        title={evidence.filename}
        subtitle={`Evidence · ${evidence.evidence_category}`}
        breadcrumbs={[
          { label: "Evidence Review", href: "/evidence-review" },
          { label: evidence.filename },
        ]}
        action={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push(`/audits/${evidence.audit_id}/evidence`)}
          >
            <ArrowLeft size={12} />
            Back to Audit Evidence
          </Button>
        }
      />

      {/* Status + readiness */}
      <Card className="mb-6">
        <div className="flex items-center gap-6 mb-4">
          <div>
            <div className="text-12 text-neutral-400 uppercase tracking-wide mb-1">Status</div>
            <Badge variant={evidence.status} />
          </div>
          <div>
            <div className="text-12 text-neutral-400 uppercase tracking-wide mb-1">Immutable</div>
            <span className="text-14 text-neutral-800">
              {evidence.immutable_after_ready ? "Yes — locked after READY" : "No"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-6 text-14">
          <div className="flex items-center gap-2">
            <ReadinessIcon ready={evidence.extracted_text_ready} />
            <span className="text-neutral-500">Extracted text ready</span>
          </div>
          <div className="flex items-center gap-2">
            <ReadinessIcon ready={evidence.inventory_ready} />
            <span className="text-neutral-500">Inventory ready</span>
          </div>
        </div>

        {evidence.processing_error && (
          <div className="mt-4 pt-3 border-t border-neutral-200">
            <div className="text-12 text-neutral-400 uppercase tracking-wide mb-1.5">
              Processing Error
            </div>
            <div className="text-14 text-danger-dark bg-danger-light border border-danger-base/20 rounded px-3 py-2 mono">
              {evidence.processing_error}
            </div>
          </div>
        )}
      </Card>

      {/* Metadata */}
      <Card className="mb-6">
        <SectionHeader title="Evidence Metadata" />
        <MetaRow label="Evidence ID" value={evidence.evidence_id} mono />
        <MetaRow label="Audit ID" value={evidence.audit_id} mono />
        <MetaRow label="Tenant ID" value={evidence.tenant_id} mono />
        <MetaRow label="Filename" value={evidence.filename} />
        <MetaRow label="Content Type" value={evidence.content_type} mono />
        <MetaRow label="Byte Size" value={formatBytes(evidence.byte_size)} />
        <MetaRow label="SHA-256" value={evidence.sha256} mono />
        <MetaRow label="Version" value={evidence.version_number} />
        <MetaRow label="Supersedes" value={evidence.supersedes_id} mono />
        <MetaRow label="Storage Path" value={evidence.storage_path} mono />
        <MetaRow label="Note" value={evidence.note} />
        <MetaRow label="Created" value={formatDate(evidence.created_at)} />
        <MetaRow label="Updated" value={formatDate(evidence.updated_at)} />
      </Card>

      {/* OCR submission */}
      {canSubmitOcr && (
        <Card>
          <SectionHeader
            title="Manual OCR Text Submission"
            subtitle="Submit OCR-extracted text for this evidence item when automated extraction is not possible."
          />

          <form onSubmit={handleOcrSubmit} className="space-y-4">
            <div>
              <label className="block text-13 font-medium text-neutral-600 mb-1.5">
                OCR Text
              </label>
              <textarea
                rows={10}
                className="w-full px-3 py-2 border border-neutral-200 rounded-base bg-white text-14 text-neutral-800 mono placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-base resize-y"
                placeholder="Paste the extracted text from the document…"
                value={ocrText}
                onChange={(e) => setOcrText(e.target.value)}
              />
            </div>

            {ocrResult && (
              <div className="text-14 text-success-dark bg-success-light border border-success-base/20 rounded px-3 py-2">
                {ocrResult}
              </div>
            )}
            {ocrError && (
              <div className="text-14 text-danger-dark bg-danger-light border border-danger-base/20 rounded px-3 py-2">
                {ocrError}
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              loading={ocrLoading}
              disabled={!ocrText.trim()}
            >
              Submit OCR Text
            </Button>
          </form>
        </Card>
      )}

      {evidence.status === "READY" && (
        <Card>
          <div className="flex items-center gap-2 text-14 text-success-dark">
            <CheckCircle2 size={15} />
            This evidence item is READY and immutable. No further operator action is required.
          </div>
        </Card>
      )}
    </>
  );
}
