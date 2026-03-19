"use client";

import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  getPreparationSummary,
  ensureRequirements,
  listModelCalls,
  getAudit,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { BlockingBanner } from "@/components/ui/BlockingBanner";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Button } from "@/components/ui/Button";
import { PageSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { StatRow } from "@/components/ui/StatRow";
import { formatDate } from "@/lib/utils";
import { useState } from "react";
import type { EvidenceChecklistItem, ModelCallLogRow } from "@/lib/types";
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  FileQuestion,
  ChevronRight,
} from "lucide-react";

function ChecklistItemRow({ item, auditId }: { item: EvidenceChecklistItem; auditId: string }) {
  const router = useRouter();
  const isReady = item.status === "READY";

  return (
    <div className="flex items-start gap-3 py-3 border-b border-neutral-100 last:border-0">
      <div className="mt-0.5 flex-none">
        {isReady ? (
          <CheckCircle2 size={15} className="text-success-base" />
        ) : item.status === "MISSING" ? (
          <FileQuestion size={15} className="text-neutral-400" />
        ) : item.status === "PROCESSING" || item.status === "UPLOADING" ? (
          <Clock size={15} className="text-info-base" />
        ) : (
          <AlertCircle size={15} className="text-danger-base" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2.5 mb-0.5">
          <span className="text-14 font-medium text-neutral-800">{item.label}</span>
          <Badge variant={item.status} />
          <span className="text-12 text-neutral-400 font-mono">{item.required_category}</span>
        </div>

        {item.blocking_reasons.length > 0 && !isReady && (
          <ul className="mt-1 space-y-0.5">
            {item.blocking_reasons.map((r, i) => (
              <li key={i} className="text-13 text-neutral-500">
                · {r}
              </li>
            ))}
          </ul>
        )}

        {item.linked_evidence_ids.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {item.linked_evidence_ids.map((eid) => (
              <button
                key={eid}
                onClick={() => router.push(`/audits/${auditId}/evidence`)}
                className="font-mono text-12 text-neutral-400 hover:text-brand-600 transition-colors duration-base"
              >
                {eid}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex-none text-neutral-400">
        <ChevronRight size={13} />
      </div>
    </div>
  );
}

function ModelCallsSection({ auditId, userId }: { auditId: string; userId: string }) {
  const [open, setOpen] = useState(false);
  const { data: calls, error } = useSWR(
    open ? ["model-calls", auditId, userId] : null,
    ([, id, uid]) => listModelCalls(uid, id),
  );

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-14 text-neutral-500 hover:text-neutral-800 transition-colors duration-base"
      >
        <ChevronRight
          size={13}
          className={`transition-transform duration-base ${open ? "rotate-90" : ""}`}
        />
        Model Call Log
      </button>

      {open && (
        <div className="mt-3 border border-neutral-200 rounded-base overflow-hidden">
          {error ? (
            <p className="px-4 py-3 text-14 text-neutral-400">Failed to load.</p>
          ) : !calls ? (
            <p className="px-4 py-3 text-14 text-neutral-400">Loading…</p>
          ) : calls.length === 0 ? (
            <p className="px-4 py-3 text-14 text-neutral-400">No model calls recorded.</p>
          ) : (
            <table className="w-full text-13">
              <thead className="bg-neutral-50 border-b border-neutral-200">
                <tr>
                  {["Surface", "Action", "Model", "Status", "Timestamp"].map((h) => (
                    <th key={h} className="px-3 py-2 text-left text-11 font-medium text-neutral-500 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-neutral-100">
                {calls.map((call: ModelCallLogRow) => (
                  <tr key={call.call_id}>
                    <td className="px-3 py-2 font-mono text-neutral-700">{call.surface}</td>
                    <td className="px-3 py-2 text-neutral-600">{call.action}</td>
                    <td className="px-3 py-2 text-neutral-400">{call.model_name}</td>
                    <td className="px-3 py-2">
                      <Badge variant={call.status} />
                    </td>
                    <td className="px-3 py-2 text-neutral-400">
                      {formatDate(call.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

export default function AuditPreparationPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { userId } = useAuth();
  const router = useRouter();
  const [ensureLoading, setEnsureLoading] = useState(false);

  const {
    data: summary,
    error,
    isLoading,
    mutate,
  } = useSWR(
    userId && auditId ? ["prep", auditId, userId] : null,
    ([, id, uid]) => getPreparationSummary(uid, id),
    { refreshInterval: 10_000 },
  );

  const { data: audit } = useSWR(
    userId && auditId ? ["audit", auditId, userId] : null,
    ([, id, uid]) => getAudit(uid, id),
  );

  async function handleEnsure() {
    setEnsureLoading(true);
    try {
      await ensureRequirements(userId!, auditId);
      await mutate();
    } finally {
      setEnsureLoading(false);
    }
  }

  if (isLoading) return <PageSkeleton />;
  if (error)
    return <ErrorMessage message={error.message} onRetry={() => mutate()} />;
  if (!summary) return null;

  const isBlocked = summary.preparation_status === "BLOCKED";

  return (
    <>
      <PageHeader
        title="Audit Preparation"
        subtitle={audit?.system_name}
        breadcrumbs={[
          { label: "Audits", href: "/audits" },
          { label: audit?.system_name ?? auditId, href: `/audits/${auditId}` },
          { label: "Preparation" },
        ]}
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleEnsure}
              loading={ensureLoading}
            >
              Refresh Requirements
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => router.push(`/audits/${auditId}/evidence`)}
            >
              Manage Evidence
            </Button>
          </div>
        }
      />

      {isBlocked && (
        <BlockingBanner
          className="mb-6"
          title="Audit preparation is not ready — run is blocked"
          reasons={summary.blocking_reasons}
          variant="error"
        />
      )}

      {/* Stats */}
      <Card className="mb-6">
        <div className="flex items-center justify-between">
          <StatRow
            stats={[
              {
                label: "requirements",
                value: summary.total_requirements,
                variant: "default",
              },
              {
                label: "ready",
                value: summary.total_ready,
                variant: "success",
              },
              {
                label: "blocked",
                value: summary.total_blocked,
                variant: summary.total_blocked > 0 ? "error" : "muted",
              },
            ]}
          />
          <Badge variant={summary.preparation_status} />
        </div>
      </Card>

      {/* Checklist */}
      <Card className="mb-6" padding={false}>
        <div className="px-5 py-4 border-b border-neutral-200">
          <SectionHeader
            title="Evidence Requirements Checklist"
            subtitle="Each required category must have at least one READY evidence file."
          />
        </div>
        <div className="px-5">
          {summary.checklist.length === 0 ? (
            <div className="py-8 text-center text-14 text-neutral-400">
              No requirements configured.{" "}
              <button
                onClick={handleEnsure}
                className="text-brand-600 hover:underline"
              >
                Initialize requirements
              </button>
            </div>
          ) : (
            summary.checklist.map((item) => (
              <ChecklistItemRow
                key={item.requirement_id}
                item={item}
                auditId={auditId}
              />
            ))
          )}
        </div>
      </Card>

      {/* Model Call Log */}
      <Card>
        <ModelCallsSection auditId={auditId} userId={userId!} />
      </Card>
    </>
  );
}
