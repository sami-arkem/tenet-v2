"use client";

import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  getRemediationDetail,
  assignRemediationOwner,
  setRemediationDueDate,
  transitionRemediationStatus,
  applyVerificationResult,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Button } from "@/components/ui/Button";
import { PageSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { formatDate, formatDateOnly } from "@/lib/utils";
import { useState } from "react";
import { ArrowLeft, Clock, User, AlertTriangle } from "lucide-react";
import type { TimelineEvent } from "@/lib/types";

const STATUS_TRANSITIONS: Record<string, string[]> = {
  OPEN: ["IN_PROGRESS", "NOT_APPLICABLE"],
  IN_PROGRESS: ["RESOLVED", "OPEN"],
  RESOLVED: ["OPEN"],
  NOT_APPLICABLE: ["OPEN"],
};


const INPUT_CLS =
  "w-full px-3 py-2 border border-neutral-200 rounded-base bg-white text-14 text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-base";

function TimelineRow({ event }: { event: TimelineEvent }) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-neutral-200 last:border-0">
      <div className="w-2 h-2 rounded-full bg-neutral-300 mt-2 flex-none" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-11 font-medium text-neutral-800 mono">
            {event.event_type}
          </span>
          {event.to_status && (
            <Badge variant={event.to_status} />
          )}
          <span className="text-12 text-neutral-400">
            {event.actor_user_id}
          </span>
        </div>
        {event.note && (
          <p className="text-12 text-neutral-500">{event.note}</p>
        )}
        <div className="text-12 text-neutral-400 mt-1">
          {formatDate(event.created_at)}
        </div>
      </div>
    </div>
  );
}

export default function RemediationDetailPage() {
  const { remediationId } = useParams<{ remediationId: string }>();
  const { userId } = useAuth();
  const router = useRouter();

  const {
    data: detail,
    error,
    isLoading,
    mutate,
  } = useSWR(
    userId && remediationId ? ["remediation-detail", remediationId, userId] : null,
    ([, id, uid]) => getRemediationDetail(uid, id),
    { refreshInterval: 15_000 },
  );

  // Owner assignment
  const [ownerUserId, setOwnerUserId] = useState("");
  const [ownerNote, setOwnerNote] = useState("");
  const [ownerLoading, setOwnerLoading] = useState(false);
  const [ownerError, setOwnerError] = useState<string | null>(null);

  // Due date
  const [dueDate, setDueDate] = useState("");
  const [dueDateNote, setDueDateNote] = useState("");
  const [dueDateLoading, setDueDateLoading] = useState(false);
  const [dueDateError, setDueDateError] = useState<string | null>(null);

  // Status transition
  const [toStatus, setToStatus] = useState("");
  const [statusNote, setStatusNote] = useState("");
  const [statusLoading, setStatusLoading] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  // Verification
  const [verificationPassed, setVerificationPassed] = useState<boolean | null>(null);
  const [verificationNote, setVerificationNote] = useState("");
  const [verificationLoading, setVerificationLoading] = useState(false);
  const [verificationError, setVerificationError] = useState<string | null>(null);

  async function handleAssignOwner(e: React.FormEvent) {
    e.preventDefault();
    if (!ownerUserId.trim() || ownerNote.length < 10) {
      setOwnerError("User ID and note (min 10 chars) required.");
      return;
    }
    setOwnerLoading(true);
    setOwnerError(null);
    try {
      await assignRemediationOwner(userId!, remediationId, ownerUserId.trim(), ownerNote);
      await mutate();
      setOwnerUserId("");
      setOwnerNote("");
    } catch (err: unknown) {
      setOwnerError(err instanceof Error ? err.message : "Failed.");
    } finally {
      setOwnerLoading(false);
    }
  }

  async function handleSetDueDate(e: React.FormEvent) {
    e.preventDefault();
    if (!dueDate || dueDateNote.length < 10) {
      setDueDateError("Date and note (min 10 chars) required.");
      return;
    }
    setDueDateLoading(true);
    setDueDateError(null);
    try {
      await setRemediationDueDate(userId!, remediationId, dueDate, dueDateNote);
      await mutate();
      setDueDateNote("");
    } catch (err: unknown) {
      setDueDateError(err instanceof Error ? err.message : "Failed.");
    } finally {
      setDueDateLoading(false);
    }
  }

  async function handleStatusTransition(e: React.FormEvent) {
    e.preventDefault();
    if (!toStatus || statusNote.length < 10) {
      setStatusError("Target status and note (min 10 chars) required.");
      return;
    }
    setStatusLoading(true);
    setStatusError(null);
    try {
      await transitionRemediationStatus(userId!, remediationId, toStatus, statusNote);
      await mutate();
      setToStatus("");
      setStatusNote("");
    } catch (err: unknown) {
      setStatusError(err instanceof Error ? err.message : "Failed.");
    } finally {
      setStatusLoading(false);
    }
  }

  async function handleVerification(passed: boolean) {
    setVerificationLoading(true);
    setVerificationError(null);
    try {
      await applyVerificationResult(
        userId!,
        remediationId,
        passed,
        verificationNote || undefined,
      );
      await mutate();
      setVerificationNote("");
      setVerificationPassed(null);
    } catch (err: unknown) {
      setVerificationError(err instanceof Error ? err.message : "Failed.");
    } finally {
      setVerificationLoading(false);
    }
  }

  if (isLoading) return <PageSkeleton />;
  if (error)
    return <ErrorMessage message={error.message} onRetry={() => mutate()} />;
  if (!detail) return null;

  const item = detail.item;
  const timeline: TimelineEvent[] = detail.timeline ?? [];
  const currentStatus = item.status?.toUpperCase() ?? "OPEN";
  const availableTransitions = STATUS_TRANSITIONS[currentStatus] ?? [];

  return (
    <>
      <PageHeader
        title={item.title}
        subtitle={`Remediation · ${item.audit_id}`}
        breadcrumbs={[
          { label: "Remediation", href: "/remediation" },
          { label: item.title },
        ]}
        action={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push("/remediation")}
          >
            <ArrowLeft size={12} />
            Dashboard
          </Button>
        }
      />

      {/* Status strip */}
      <Card className="mb-6">
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <div className="text-12 text-neutral-400 uppercase tracking-wide mb-1">Status</div>
            <Badge variant={item.status} />
          </div>
          <div>
            <div className="text-12 text-neutral-400 uppercase tracking-wide mb-1">Severity</div>
            <span className="text-14 text-neutral-800 font-medium">{item.severity}</span>
          </div>
          <div>
            <div className="text-12 text-neutral-400 uppercase tracking-wide mb-1">Owner</div>
            <span className="text-14 mono text-neutral-500">
              {item.owner_user_id ?? "Unassigned"}
            </span>
          </div>
          <div>
            <div className="text-12 text-neutral-400 uppercase tracking-wide mb-1">Due Date</div>
            <span className="text-14 text-neutral-500">
              {item.due_date ? formatDateOnly(item.due_date) : "Not set"}
            </span>
          </div>
          {item.release_blocking && (
            <div className="flex items-center gap-1.5 text-sm text-danger-dark">
              <AlertTriangle size={13} />
              Release-blocking
            </div>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-neutral-200">
          <div className="text-12 text-neutral-400 uppercase tracking-wide mb-2">Gap / Finding</div>
          <p className="text-14 text-neutral-500">{item.gap_note}</p>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-6">
          {/* Assign owner */}
          <Card>
            <SectionHeader
              title="Assign Owner"
              subtitle="Assign a user responsible for this remediation."
            />
            <form onSubmit={handleAssignOwner} className="space-y-3">
              <div>
                <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wide mb-1.5">
                  <User size={11} className="inline mr-1" />
                  User ID
                </label>
                <input
                  type="text"
                  className={INPUT_CLS}
                  placeholder="e.g. user_alice"
                  value={ownerUserId}
                  onChange={(e) => setOwnerUserId(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wide mb-1.5">
                  Note (min 10 chars)
                </label>
                <input
                  type="text"
                  className={INPUT_CLS}
                  placeholder="Reason for assignment…"
                  value={ownerNote}
                  onChange={(e) => setOwnerNote(e.target.value)}
                />
              </div>
              {ownerError && (
                <p className="text-12 text-danger-dark">{ownerError}</p>
              )}
              <Button type="submit" variant="secondary" size="sm" loading={ownerLoading}>
                Assign Owner
              </Button>
            </form>
          </Card>

          {/* Set due date */}
          <Card>
            <SectionHeader title="Set Due Date" />
            <form onSubmit={handleSetDueDate} className="space-y-3">
              <div>
                <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wide mb-1.5">
                  <Clock size={11} className="inline mr-1" />
                  Due Date
                </label>
                <input
                  type="date"
                  className={INPUT_CLS}
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wide mb-1.5">
                  Note (min 10 chars)
                </label>
                <input
                  type="text"
                  className={INPUT_CLS}
                  placeholder="Reason for this due date…"
                  value={dueDateNote}
                  onChange={(e) => setDueDateNote(e.target.value)}
                />
              </div>
              {dueDateError && (
                <p className="text-12 text-danger-dark">{dueDateError}</p>
              )}
              <Button type="submit" variant="secondary" size="sm" loading={dueDateLoading}>
                Set Due Date
              </Button>
            </form>
          </Card>

          {/* Status transition */}
          {availableTransitions.length > 0 && (
            <Card>
              <SectionHeader
                title="Status Transition"
                subtitle={`Current: ${currentStatus}`}
              />
              <form onSubmit={handleStatusTransition} className="space-y-3">
                <div>
                  <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wide mb-1.5">
                    Transition To
                  </label>
                  <select
                    className={INPUT_CLS}
                    value={toStatus}
                    onChange={(e) => setToStatus(e.target.value)}
                  >
                    <option value="">Select…</option>
                    {availableTransitions.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wide mb-1.5">
                    Note (min 10 chars)
                  </label>
                  <input
                    type="text"
                    className={INPUT_CLS}
                    placeholder="Reason for status change…"
                    value={statusNote}
                    onChange={(e) => setStatusNote(e.target.value)}
                  />
                </div>
                {statusError && (
                  <p className="text-12 text-danger-dark">{statusError}</p>
                )}
                <Button type="submit" variant="primary" size="sm" loading={statusLoading}>
                  Apply Transition
                </Button>
              </form>
            </Card>
          )}

          {/* Verification */}
          <Card>
            <SectionHeader
              title="Verification Result"
              subtitle="Record whether the remediation has been verified as effective."
            />
            <div className="space-y-3">
              <div>
                <label className="block text-11 font-medium text-neutral-500 uppercase tracking-wide mb-1.5">
                  Note (optional)
                </label>
                <input
                  type="text"
                  className={INPUT_CLS}
                  placeholder="Optional updated gap note…"
                  value={verificationNote}
                  onChange={(e) => setVerificationNote(e.target.value)}
                />
              </div>
              {verificationError && (
                <p className="text-12 text-danger-dark">{verificationError}</p>
              )}
              <div className="flex items-center gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  loading={verificationLoading}
                  onClick={() => handleVerification(true)}
                >
                  Mark Passed
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  loading={verificationLoading}
                  onClick={() => handleVerification(false)}
                >
                  Mark Failed
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Timeline */}
        <div>
          <Card>
            <SectionHeader
              title="Immutable Timeline"
              subtitle="All operator actions are permanently recorded."
            />
            {timeline.length === 0 ? (
              <p className="text-14 text-neutral-400">No events recorded yet.</p>
            ) : (
              <div>
                {timeline.map((event) => (
                  <TimelineRow key={event.event_id} event={event} />
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
