// Findings — Bible §3 standalone cross-audit findings view
// All open findings across all audits, filterable by severity/status/regime
"use client";

import useSWR from "swr";
import { useRouter } from "next/navigation";
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
  const s = (severity ?? "LOW").toUpperCase();
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
        <Badge variant={(finding.severity ?? "low").toLowerCase()} />
        <Badge variant={(finding.verdict ?? "open").toLowerCase()} />
      </div>
      <div>
        <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1">Control</p>
        <p className="text-14 font-medium text-neutral-800">{finding.control_name}</p>
        <p className="text-13 font-mono text-neutral-400 mt-0.5">{finding.control_id}</p>
      </div>
      <div>
        <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1">Regime / Jurisdiction</p>
        <p className="text-14 text-neutral-700">{finding.regime} · {finding.jurisdiction}</p>
      </div>
      <div>
        <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1">Finding</p>
        <p className="text-14 text-neutral-700 leading-relaxed">{finding.finding}</p>
      </div>
      {finding.gap && (
        <div>
          <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1">Gap</p>
          <p className="text-13 text-neutral-600 leading-relaxed whitespace-pre-wrap">{finding.gap}</p>
        </div>
      )}
      {finding.recommended_action && (
        <div>
          <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1">Recommended Action</p>
          <p className="text-13 text-neutral-600 leading-relaxed whitespace-pre-wrap">{finding.recommended_action}</p>
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
  regime: string;
};

type AuditListItem = {
  audit_id: string;
  status: string;
};

function isAuditListItem(value: unknown): value is AuditListItem {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.audit_id === "string" && typeof candidate.status === "string";
}

export default function FindingsPage() {
  const { userId } = useAuth();
  const router = useRouter();
  const [selectedFinding, setSelectedFinding] = useState<FindingRow | null>(null);
  const [filters, setFilters] = useState<Filters>({ severity: "", regime: "" });

  const { data: auditsResponse, isLoading: auditsLoading } = useSWR(
    userId ? ["audits-findings", userId] : null,
    ([, uid]) => listAudits(uid!),
  );

  const auditItems: unknown[] = (() => {
    if (Array.isArray(auditsResponse)) return auditsResponse;
    if (typeof auditsResponse === "object" && auditsResponse !== null && "items" in auditsResponse) {
      const candidate = (auditsResponse as { items?: unknown }).items;
      return Array.isArray(candidate) ? candidate : [];
    }
    return [];
  })();

  const audits: AuditListItem[] = auditItems.filter(isAuditListItem);

  // Collect findings across all completed audits
  const completedAudits = audits.filter((audit) =>
    ["COMPLETE", "COMPLETED", "BLOCKED", "PARTIAL"].includes(audit.status),
  );

  const { data: findingsData, isLoading: findingsLoading, error } = useSWR(
    completedAudits.length > 0 && userId
      ? ["cross-findings", completedAudits.map((a) => a.audit_id).join(","), userId]
      : null,
    async ([, , uid]) => {
      const all: FindingRow[] = [];
      for (const audit of completedAudits.slice(0, 10)) {
        try {
          const res = await listFindings(uid as string, audit.audit_id);
          all.push(...(res.items ?? []));
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
    .filter((f) => !filters.severity || (f.severity ?? "").toUpperCase() === filters.severity)
    .filter((f) => !filters.regime || (f.regime ?? "").toUpperCase() === filters.regime)
    .sort(
      (a, b) =>
        (SEVERITY_ORDER[(a.severity ?? "LOW").toUpperCase()] ?? 99) -
        (SEVERITY_ORDER[(b.severity ?? "LOW").toUpperCase()] ?? 99),
    );

  const hasFilters = !!filters.severity || !!filters.regime;
  const isLoading = auditsLoading || findingsLoading;

  const clearFilters = useCallback(() => setFilters({ severity: "", regime: "" }), []);

  const severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
  const regimes = Array.from(new Set(findings.map((f) => (f.regime ?? "").toUpperCase()))).sort();

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
            const count = findings.filter((f) => (f.severity ?? "").toUpperCase() === s).length;
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
      {regimes.length > 1 && (
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <Filter className="h-4 w-4 text-neutral-400" />
          {regimes.map((r) => (
            <button
              key={r}
              onClick={() =>
                setFilters((prev) => ({ ...prev, regime: prev.regime === r ? "" : r }))
              }
              className={cn(
                "px-3 py-1.5 rounded-base text-13 font-medium border transition-colors duration-base",
                filters.regime === r
                  ? "bg-brand-50 border-brand-200 text-brand-600"
                  : "bg-white border-neutral-200 text-neutral-500 hover:border-neutral-300",
              )}
            >
              {r}
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
                {["Control", "Regime", "Severity", "Verdict"].map((h) => (
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
                const isSelected = selectedFinding?.id === finding.id;
                return (
                  <tr
                    key={finding.id}
                    onClick={() => setSelectedFinding(isSelected ? null : finding)}
                    className={cn(
                      "h-[52px] cursor-pointer transition-colors duration-base",
                      SEVERITY_LEFT_BORDER[(finding.severity ?? "LOW").toUpperCase()],
                      isSelected ? "bg-brand-50" : "hover:bg-neutral-50",
                    )}
                  >
                    <td className="px-4 py-0">
                      <div className="flex items-center gap-2">
                        <SeverityIcon severity={finding.severity ?? "low"} />
                        <div>
                          <p className="text-14 font-medium text-neutral-800">
                            {finding.control_name}
                          </p>
                          <p className="text-12 text-neutral-400">{finding.control_id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-0 text-13 text-neutral-500">
                      {finding.regime}
                    </td>
                    <td className="px-4 py-0">
                      <Badge variant={(finding.severity ?? "low").toLowerCase()} />
                    </td>
                    <td className="px-4 py-0">
                      <Badge variant={(finding.verdict ?? "open").toLowerCase()} />
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
        title={selectedFinding?.control_name ?? "Finding"}
      >
        {selectedFinding && <FindingDetail finding={selectedFinding} />}
      </DetailPanel>
    </>
  );
}
