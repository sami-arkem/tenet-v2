// Findings — Bible §3 standalone cross-audit findings view
// All open findings across all audits, filterable by severity/status/regime
"use client";

import useSWR from "swr";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { useCallback, useState } from "react";
import { listAudits, listFindings } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DetailPanel } from "@/components/ui/DetailPanel";
import { PageSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  Flame,
  Info,
  Filter,
  X,
  ArrowRight,
} from "lucide-react";
import type { FindingRow } from "@/lib/types";

const SEVERITY_ORDER: Record<string, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
};

const SEVERITY_LEFT_BORDER: Record<string, string> = {
  CRITICAL: "border-l-[3px] border-l-danger-base",
  HIGH: "border-l-[2px] border-l-warning-base",
  MEDIUM: "border-l-[2px] border-l-warning-base",
  LOW: "border-l border-l-neutral-200",
};

const SEVERITY_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  CRITICAL: Flame,
  HIGH: AlertTriangle,
  MEDIUM: Info,
  LOW: Info,
};

function SeverityIcon({ severity }: { severity: string }) {
  const s = severity.toUpperCase();
  const Icon = SEVERITY_ICON[s] ?? Info;
  const cls =
    s === "CRITICAL" ? "text-danger-base" :
    s === "HIGH" ? "text-warning-base" :
    s === "MEDIUM" ? "text-warning-base" :
    "text-neutral-400";
  return <Icon className={cn("h-4 w-4", cls)} />;
}

function FindingDetail({ finding }: { finding: FindingRow }) {
  const router = useRouter();
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant={finding.severity.toLowerCase()} />
        <Badge variant={finding.finding_type.toLowerCase()} />
      </div>
      <div>
        <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1">Control</p>
        <p className="text-14 font-medium text-neutral-800">{finding.finding_type}</p>
        <p className="text-13 font-mono text-neutral-400 mt-0.5">{finding.finding_id}</p>
      </div>
      <div>
        <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1">Finding</p>
        <p className="text-14 text-neutral-700 leading-relaxed">{finding.title}</p>
      </div>
      {finding.detail && (
        <div>
          <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1">Detail</p>
          <p className="text-13 text-neutral-600 leading-relaxed whitespace-pre-wrap">{finding.detail}</p>
        </div>
      )}
      <Button
        variant="secondary"
        size="sm"
        iconRight={<ArrowRight />}
        onClick={() => router.push("/remediation")}
        fullWidth
      >
        Move to Remediation
      </Button>
    </div>
  );
}

type Filters = {
  severity: string;
  type: string;
};

type AuditListItem = {
  audit_id: string;
  status: string;
};

function isAuditListItem(value: unknown): value is AuditListItem {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return typeof candidate.audit_id === "string" && typeof candidate.status === "string";
}

export default function FindingsPage() {
  const { userId } = useAuth();
  const router = useRouter();
  const [selectedFinding, setSelectedFinding] = useState<FindingRow | null>(null);
  const [filters, setFilters] = useState<Filters>({ severity: "", type: "" });

  const { data: auditsResponse, isLoading: auditsLoading } = useSWR(
    userId ? ["audits-findings", userId] : null,
    ([, uid]) => listAudits(uid!),
  );

  const auditItems: unknown[] = (() => {
    if (Array.isArray(auditsResponse)) {
      return auditsResponse;
    }

    if (typeof auditsResponse === "object" && auditsResponse !== null && "items" in auditsResponse) {
      const candidate = (auditsResponse as { items?: unknown }).items;
      return Array.isArray(candidate) ? candidate : [];
    }

    return [];
  })();

  const audits: AuditListItem[] = auditItems.filter(isAuditListItem);

  // Collect findings across all completed audits
  const completedAudits = audits.filter((audit) =>
    ["COMPLETE", "COMPLETED", "BLOCKED"].includes(audit.status),
  );

  const { data: findingsData, isLoading: findingsLoading, error } = useSWR(
    completedAudits.length > 0 && userId
      ? ["cross-findings", completedAudits.map((a) => a.audit_id).join(","), userId]
      : null,
    async ([, , uid]) => {
      const all: FindingRow[] = [];
      for (const audit of completedAudits.slice(0, 10)) {
        try {
          const res = await listFindings(audit.audit_id, uid as string);
          all.push(...(res.rows ?? []));
        } catch {
          // skip failed audits
        }
      }
      return all;
    },
  );

  const findings = findingsData ?? [];

  // Apply filters
  const filtered = findings
    .filter((f) => !filters.severity || f.severity.toUpperCase() === filters.severity)
    .filter((f) => !filters.type || f.finding_type.toUpperCase() === filters.type)
    .sort(
      (a, b) =>
        (SEVERITY_ORDER[a.severity.toUpperCase()] ?? 99) -
        (SEVERITY_ORDER[b.severity.toUpperCase()] ?? 99),
    );

  const hasFilters = !!filters.severity || !!filters.type;
  const isLoading = auditsLoading || findingsLoading;

  const clearFilters = useCallback(() => setFilters({ severity: "", type: "" }), []);

  const severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
  const types = Array.from(new Set(findings.map((f) => f.finding_type.toUpperCase()))).sort();

  if (isLoading) return <PageSkeleton />;
  if (error) return <ErrorMessage message="Failed to load findings." />;

  return (
    <>
      <PageHeader
        title="Findings"
        subtitle="Open findings across all audits"
        action={
          hasFilters ? (
            <Button variant="ghost" size="sm" iconLeft={<X />} onClick={clearFilters}>
              Clear filters
            </Button>
          ) : undefined
        }
      />

      {/* Summary stats */}
      {findings.length > 0 && (
        <div className="flex gap-4 mb-6 flex-wrap">
          {severities.map((s) => {
            const count = findings.filter((f) => f.severity.toUpperCase() === s).length;
            if (count === 0) return null;
            return (
              <button
                key={s}
                onClick={() =>
                  setFilters((prev) => ({
                    ...prev,
                    severity: prev.severity === s ? "" : s,
                  }))
                }
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded-base border text-14 font-medium transition-colors duration-base",
                  filters.severity === s
                    ? "bg-brand-50 border-brand-200 text-brand-600"
                    : "bg-white border-neutral-200 text-neutral-600 hover:border-neutral-300",
                )}
              >
                <SeverityIcon severity={s} />
                <span>{count}</span>
                <span className="text-13 text-neutral-400">{s}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Filter toolbar */}
      {types.length > 1 && (
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <Filter className="h-4 w-4 text-neutral-400" />
          {types.map((t) => (
            <button
              key={t}
              onClick={() =>
                setFilters((prev) => ({ ...prev, type: prev.type === t ? "" : t }))
              }
              className={cn(
                "px-3 py-1.5 rounded-base text-13 font-medium border transition-colors duration-base",
                filters.type === t
                  ? "bg-brand-50 border-brand-200 text-brand-600"
                  : "bg-white border-neutral-200 text-neutral-500 hover:border-neutral-300",
              )}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {/* Empty states */}
      {completedAudits.length === 0 && (
        <EmptyState
          title="No completed audits"
          description="Run your first audit to see findings here."
          action={
            <Button
              variant="primary"
              size="sm"
              onClick={() => router.push("/audits/new")}
            >
              New Audit
            </Button>
          }
        />
      )}

      {completedAudits.length > 0 && filtered.length === 0 && (
        <EmptyState
          title={hasFilters ? "No findings match your filters" : "No findings"}
          description={
            hasFilters
              ? "Try clearing the filters to see all findings."
              : "All controls are passing. Great work."
          }
          action={
            hasFilters ? (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                Clear filters
              </Button>
            ) : undefined
          }
        />
      )}

      {/* Findings table */}
      {filtered.length > 0 && (
        <Card padding={false}>
          <table className="w-full">
            <thead>
              <tr className="bg-neutral-50 border-b border-neutral-200">
                {["Control", "Regime / Type", "Severity", "Status"].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-11 font-medium text-neutral-500 uppercase tracking-wider"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {filtered.map((finding) => {
                const isSelected = selectedFinding?.finding_id === finding.finding_id;
                return (
                  <tr
                    key={finding.finding_id}
                    onClick={() => setSelectedFinding(isSelected ? null : finding)}
                    className={cn(
                      "h-[52px] cursor-pointer transition-colors duration-base",
                      SEVERITY_LEFT_BORDER[finding.severity.toUpperCase()],
                      isSelected
                        ? "bg-brand-50"
                        : "hover:bg-neutral-50",
                    )}
                  >
                    <td className="px-4 py-0">
                      <div className="flex items-center gap-2">
                        <SeverityIcon severity={finding.severity} />
                        <div>
                          <p className="text-14 font-medium text-neutral-800">
                            {finding.finding_id}
                          </p>
                          <p className="text-12 text-neutral-400">{finding.title}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-0 text-13 text-neutral-500">
                      {finding.finding_type}
                    </td>
                    <td className="px-4 py-0">
                      <Badge variant={finding.severity.toLowerCase()} />
                    </td>
                    <td className="px-4 py-0">
                      <Badge variant="open" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {filtered.length > 0 && (
            <div className="px-4 py-3 border-t border-neutral-100">
              <p className="text-13 text-neutral-400">
                Showing {filtered.length} of {findings.length} finding{findings.length !== 1 ? "s" : ""}
              </p>
            </div>
          )}
        </Card>
      )}

      {/* Detail panel */}
      <DetailPanel
        isOpen={!!selectedFinding}
        onClose={() => setSelectedFinding(null)}
        title={selectedFinding?.finding_type ?? "Finding"}
      >
        {selectedFinding && <FindingDetail finding={selectedFinding} />}
      </DetailPanel>
    </>
  );
}
