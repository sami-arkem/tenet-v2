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
import { StatusBadge } from "@/components/ui/StatusBadge";
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
    <div className="flex items-start gap-3 py-3 border-b border-surface-border last:border-0">
      <div className="mt-0.5 flex-none">
        {isReady ? (
          <CheckCircle2 size={15} className="text-emerald-600" />
        ) : item.status === "MISSING" ? (
          <FileQuestion size={15} className="text-gray-400" />
        ) : item.status === "PROCESSING" || item.status === "UPLOADING" ? (
          <Clock size={15} className="text-blue-500" />
        ) : (
          <AlertCircle size={15} className="text-red-500" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2.5 mb-0.5">
          <span className="text-sm font-medium text-text">{item.label}</span>
          <StatusBadge status={item.status} size="sm" />
          <span className="text-xs text-text-muted mono">{item.required_category}</span>
        </div>

        {item.blocking_reasons.length > 0 && !isReady && (
          <ul className="mt-1 space-y-0.5">
            {item.blocking_reasons.map((r, i) => (
              <li key={i} className="text-xs text-text-secondary">
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
                className="mono text-[10px] text-text-muted hover:text-blue-600 transition-fast"
              >
                {eid}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex-none text-text-muted">
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
        className="flex items-center gap-2 text-sm text-text-secondary hover:text-text transition-fast"
      >
        <ChevronRight
          size={13}
          className={`transition-fast ${open ? "rotate-90" : ""}`}
        />
        Model Call Log
      </button>

      {open && (
        <div className="mt-3 border border-surface-border rounded overflow-hidden">
          {error ? (
            <p className="px-4 py-3 text-sm text-text-muted">Failed to load.</p>
          ) : !calls ? (
            <p className="px-4 py-3 text-sm text-text-muted">Loading…</p>
          ) : calls.length === 0 ? (
            <p className="px-4 py-3 text-sm text-text-muted">No model calls recorded.</p>
          ) : (
            <table className="w-full text-xs">
              <thead className="bg-surface-subtle border-b border-surface-border">
                <tr>
                  <th className="px-3 py-2 text-left text-text-muted font-medium">Surface</th>
                  <th className="px-3 py-2 text-left text-text-muted font-medium">Action</th>
                  <th className="px-3 py-2 text-left text-text-muted font-medium">Model</th>
                  <th className="px-3 py-2 text-left text-text-muted font-medium">Status</th>
                  <th className="px-3 py-2 text-left text-text-muted font-medium">Timestamp</th>
                </tr>
              </thead>
              <tbody className="bg-surface divide-y divide-surface-border">
                {calls.map((call) => (
                  <tr key={call.call_id}>
                    <td className="px-3 py-2 mono">{call.surface}</td>
                    <td className="px-3 py-2 text-text-secondary">{call.action}</td>
                    <td className="px-3 py-2 text-text-muted">{call.model_name}</td>
                    <td className="px-3 py-2">
                      <StatusBadge status={call.status} size="sm" />
                    </td>
                    <td className="px-3 py-2 text-text-muted">
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

      {/* Blocking banner — shown when preparation is not ready */}
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
          <StatusBadge status={summary.preparation_status} />
        </div>
      </Card>

      {/* Checklist */}
      <Card className="mb-6" padding={false}>
        <div className="px-5 py-4 border-b border-surface-border">
          <SectionHeader
            title="Evidence Requirements Checklist"
            subtitle="Each required category must have at least one READY evidence file."
          />
        </div>
        <div className="px-5">
          {summary.checklist.length === 0 ? (
            <div className="py-8 text-center text-sm text-text-muted">
              No requirements configured.{" "}
              <button
                onClick={handleEnsure}
                className="text-blue-600 hover:underline"
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
