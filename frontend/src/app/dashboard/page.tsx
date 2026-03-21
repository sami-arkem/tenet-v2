// Dashboard — Bible §3.3
// Posture banner + stats cards + audit list + quick actions
"use client";

import useSWR from "swr";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { listAudits, getRemediationDashboard } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";
import {
  ClipboardCheck,
  AlertTriangle,
  CheckCircle2,
  Wrench,
  Plus,
  ArrowRight,
  TrendingUp,
  Activity,
} from "lucide-react";
import type { AuditSummary } from "@/lib/types";

// ── Posture banner ────────────────────────────────────────────────────────────
function PostureBanner({
  audits,
  overdueCount,
}: {
  audits: AuditSummary[];
  overdueCount: number;
}) {
  const blockedAudits = audits.filter(
    (a) => a.status === "BLOCKED" || a.deployment_decision === "BLOCKED",
  );
  const runningAudits = audits.filter((a) => a.status === "RUNNING");

  const isRed =
    blockedAudits.length > 0 || overdueCount > 0;
  const isAmber = runningAudits.length > 0 && !isRed;

  const bg = isRed
    ? "bg-danger-light border-danger-base"
    : isAmber
      ? "bg-warning-light border-warning-base"
      : "bg-success-light border-success-base";

  const icon = isRed ? (
    <AlertTriangle className="h-5 w-5 text-danger-base" />
  ) : isAmber ? (
    <Activity className="h-5 w-5 text-warning-base" />
  ) : (
    <CheckCircle2 className="h-5 w-5 text-success-base" />
  );

  const message = isRed
    ? blockedAudits.length > 0
      ? `${blockedAudits.length} audit${blockedAudits.length !== 1 ? "s" : ""} blocked — action required before deployment`
      : `${overdueCount} overdue remediation${overdueCount !== 1 ? "s" : ""} need attention`
    : isAmber
      ? `${runningAudits.length} audit${runningAudits.length !== 1 ? "s" : ""} currently running`
      : "Your compliance posture is strong";

  return (
    <div
      className={cn(
        "flex items-center gap-3 px-5 py-4 rounded-base border mb-6",
        bg,
      )}
    >
      {icon}
      <p className="text-14 font-medium text-neutral-800">{message}</p>
    </div>
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({
  label,
  value,
  sub,
  variant = "default",
  href,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  sub?: string;
  variant?: "default" | "danger" | "warning" | "success";
  href?: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  const router = useRouter();
  const valueColor =
    variant === "danger"
      ? "text-danger-base"
      : variant === "warning"
        ? "text-warning-base"
        : variant === "success"
          ? "text-success-base"
          : "text-neutral-800";

  return (
    <div
      onClick={() => href && router.push(href)}
      className={cn(
        "bg-white border border-neutral-200 rounded-base p-5",
        href && "cursor-pointer hover:border-neutral-300 transition-colors duration-base",
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-13 text-neutral-500 font-medium uppercase tracking-wider">
            {label}
          </p>
          <p className={cn("text-28 font-medium mt-1 leading-none", valueColor)}>
            {value}
          </p>
          {sub && (
            <p className="text-13 text-neutral-400 mt-1.5">{sub}</p>
          )}
        </div>
        <div className="p-2 bg-neutral-100 rounded-base">
          <Icon className="h-5 w-5 text-neutral-500" />
        </div>
      </div>
    </div>
  );
}

// ── Recent audits table ───────────────────────────────────────────────────────
function RecentAudits({ audits }: { audits: AuditSummary[] }) {
  const router = useRouter();
  const recent = audits.slice(0, 5);

  if (recent.length === 0) return null;

  return (
    <Card padding={false}>
      <div className="px-5 py-4 border-b border-neutral-200 flex items-center justify-between">
        <h3 className="text-16 font-medium text-neutral-800">Recent Audits</h3>
        <Button
          variant="ghost"
          size="sm"
          iconRight={<ArrowRight />}
          onClick={() => router.push("/audits")}
        >
          View all
        </Button>
      </div>
      <table className="w-full">
        <thead>
          <tr className="bg-neutral-50 border-b border-neutral-200">
            {["System", "Framework", "Status", "Decision", "Updated"].map((h) => (
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
          {recent.map((audit) => (
            <tr
              key={audit.audit_id}
              onClick={() => router.push(`/audits/${audit.audit_id}`)}
              className="h-[52px] cursor-pointer hover:bg-neutral-50 transition-colors duration-base"
            >
              <td className="px-4 py-0">
                <div className="text-14 font-medium text-neutral-800">
                  {audit.system_name}
                </div>
                <div className="text-12 text-neutral-400 font-mono">
                  {audit.audit_kind}
                </div>
              </td>
              <td className="px-4 py-0 text-14 text-neutral-600">
                {audit.framework} · {audit.jurisdiction}
              </td>
              <td className="px-4 py-0">
                <Badge variant={audit.status.toLowerCase()} />
              </td>
              <td className="px-4 py-0">
                <Badge variant={audit.deployment_decision.toLowerCase()} />
              </td>
              <td className="px-4 py-0 text-13 text-neutral-400">
                {formatDate(audit.updated_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

// ── Quick actions ─────────────────────────────────────────────────────────────
function QuickActions() {
  const router = useRouter();

  const actions = [
    { label: "New Audit", icon: Plus, href: "/audits/new", variant: "primary" as const },
    { label: "View Audits", icon: ClipboardCheck, href: "/audits", variant: "secondary" as const },
    { label: "Evidence Review", icon: AlertTriangle, href: "/evidence-review", variant: "secondary" as const },
    { label: "Remediation", icon: Wrench, href: "/remediation", variant: "secondary" as const },
  ];

  return (
    <Card>
      <h3 className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-4">
        Quick Actions
      </h3>
      <div className="flex flex-col gap-2">
        {actions.map(({ label, icon: Icon, href, variant }) => (
          <Button
            key={label}
            variant={variant}
            size="sm"
            fullWidth
            iconLeft={<Icon />}
            onClick={() => router.push(href)}
          >
            {label}
          </Button>
        ))}
      </div>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { userId } = useAuth();

  const { data: auditsResponse, isLoading: auditsLoading } = useSWR(
    userId ? ["audits-dash", userId] : null,
    ([, uid]) => listAudits(uid!),
    { refreshInterval: 30_000 },
  );
  // Backend returns { items: [], total } — extract the array
  const audits: AuditSummary[] = Array.isArray(auditsResponse)
    ? auditsResponse
    : (auditsResponse as any)?.items ?? [];

  const { data: remDash } = useSWR(
    userId ? ["rem-dash", userId] : null,
    ([, uid]) => getRemediationDashboard(uid!),
    { refreshInterval: 30_000 },
  );

  const totalAudits = audits.length;
  const activeAudits = audits.filter((a) =>
    ["RUNNING", "CREATED"].includes(a.status),
  ).length;
  const blockedAudits = audits.filter(
    (a) => a.status === "BLOCKED" || a.deployment_decision === "BLOCKED",
  ).length;
  const overdueCount = remDash?.overdue_count ?? (Array.isArray(remDash?.overdue) ? remDash.overdue.length : 0);
  const openFindings = Array.isArray(remDash?.open) ? remDash.open.length : 0;

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Compliance posture overview"
      />

      {/* Posture banner */}
      {!auditsLoading && (
        <PostureBanner audits={audits} overdueCount={overdueCount} />
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Total Audits"
          value={auditsLoading ? "—" : totalAudits}
          sub={`${activeAudits} active`}
          icon={ClipboardCheck}
          href="/audits"
        />
        <StatCard
          label="Blocked"
          value={auditsLoading ? "—" : blockedAudits}
          sub="require attention"
          variant={blockedAudits > 0 ? "danger" : "default"}
          icon={AlertTriangle}
          href="/audits"
        />
        <StatCard
          label="Open Findings"
          value={openFindings}
          sub={`${overdueCount} overdue`}
          variant={overdueCount > 0 ? "warning" : "default"}
          icon={TrendingUp}
          href="/remediation"
        />
        <StatCard
          label="Resolved"
          value={remDash?.resolved?.length ?? 0}
          sub="this session"
          variant="success"
          icon={CheckCircle2}
          href="/remediation"
        />
      </div>

      {/* Main content + quick actions */}
      <div className="flex gap-6">
        <div className="flex-1 min-w-0">
          {auditsLoading ? (
            <div className="space-y-2 animate-pulse">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-[52px] bg-neutral-100 rounded-base" />
              ))}
            </div>
          ) : audits.length === 0 ? (
            <Card className="text-center py-16">
              <ClipboardCheck className="h-10 w-10 text-neutral-300 mx-auto mb-4" />
              <h3 className="text-16 font-medium text-neutral-700">
                Your compliance dashboard is ready
              </h3>
              <p className="text-14 text-neutral-400 mt-2 max-w-sm mx-auto">
                Start by running your first audit. Upload evidence and Tenet
                evaluates every control automatically.
              </p>
              <div className="mt-6">
                <Button
                  variant="primary"
                  onClick={() => window.location.assign("/audits/new")}
                >
                  Run Your First Audit
                </Button>
              </div>
            </Card>
          ) : (
            <RecentAudits audits={audits} />
          )}
        </div>

        {/* Quick actions sidebar */}
        <div className="w-48 shrink-0">
          <QuickActions />
        </div>
      </div>
    </>
  );
}
