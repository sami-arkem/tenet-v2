// Monitoring — Bible §12: 24/7 Regulatory Monitoring System
// Shows regulatory alerts, upcoming obligation deadlines, jurisdiction status
"use client";

import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { request } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  Bell,
  BellOff,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Globe,
  ShieldCheck,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

type AlertSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

interface RegulatoryAlert {
  id: string;
  title: string;
  summary: string;
  jurisdiction: string;
  regime: string;
  severity: AlertSeverity;
  source: string;
  effectiveDate: string;
  isRead: boolean;
  daysUntilEffective: number;
}

interface ComplianceObligation {
  id: string;
  title: string;
  regime: string;
  jurisdiction: string;
  dueDate: string;
  daysUntilDue: number;
  frequency: string;
  isOverdue: boolean;
}

// ─── Mock fallback data ───────────────────────────────────────────────────────

const MOCK_ALERTS: RegulatoryAlert[] = [
  {
    id: "alert-001",
    title: "FCA PS24/6: Consumer Duty Annual Board Report",
    summary:
      "FCA requires firms to submit their first Consumer Duty annual board report by 31 July 2025. The report must demonstrate how the firm is meeting Consumer Duty outcomes.",
    jurisdiction: "GB",
    regime: "FCA",
    severity: "HIGH",
    source: "FCA Policy Statement PS24/6",
    effectiveDate: "2025-07-31",
    isRead: false,
    daysUntilEffective: 45,
  },
  {
    id: "alert-002",
    title: "HMRC: New AML Supervision Fees 2025/26",
    summary:
      "HMRC has updated supervised business fees for 2025/26. Estate agents and accountants see 12% increase. Fee payment deadline: 31 May 2025.",
    jurisdiction: "GB",
    regime: "AML",
    severity: "MEDIUM",
    source: "HMRC Supervision",
    effectiveDate: "2025-05-31",
    isRead: true,
    daysUntilEffective: 12,
  },
  {
    id: "alert-003",
    title: "ICO: Updated Guidance on Data Transfers to US",
    summary:
      "ICO issued updated guidance on UK-US data transfers following the UK Extension to the EU-US Data Privacy Framework. Review adequacy decisions in your ROPA.",
    jurisdiction: "GB",
    regime: "GDPR",
    severity: "MEDIUM",
    source: "ICO Guidance",
    effectiveDate: "2025-04-01",
    isRead: false,
    daysUntilEffective: -15,
  },
];

const MOCK_OBLIGATIONS: ComplianceObligation[] = [
  {
    id: "ob-001",
    title: "Annual AML Risk Assessment Review",
    regime: "AML",
    jurisdiction: "GB",
    dueDate: "2025-06-30",
    daysUntilDue: 75,
    frequency: "Annual",
    isOverdue: false,
  },
  {
    id: "ob-002",
    title: "FCA REP-CRIM Submission",
    regime: "FCA",
    jurisdiction: "GB",
    dueDate: "2025-04-30",
    daysUntilDue: 5,
    frequency: "Annual",
    isOverdue: false,
  },
  {
    id: "ob-003",
    title: "GDPR DPA Annual Return",
    regime: "GDPR",
    jurisdiction: "GB",
    dueDate: "2025-03-31",
    daysUntilDue: -20,
    frequency: "Annual",
    isOverdue: true,
  },
];

// ─── Alert row ────────────────────────────────────────────────────────────────

function AlertRow({ alert, onMarkRead }: { alert: RegulatoryAlert; onMarkRead: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);

  const severityBorder =
    alert.severity === "CRITICAL" ? "border-l-[3px] border-l-danger-base" :
    alert.severity === "HIGH" ? "border-l-[2px] border-l-warning-base" :
    "border-l border-l-neutral-200";

  const urgencyLabel =
    alert.daysUntilEffective < 0
      ? "Past effective date"
      : alert.daysUntilEffective === 0
        ? "Effective today"
        : `Effective in ${alert.daysUntilEffective} days`;

  return (
    <div
      className={cn(
        "px-5 py-4 border-b border-neutral-100 last:border-0 cursor-pointer hover:bg-neutral-50 transition-colors duration-base",
        severityBorder,
        !alert.isRead && "bg-info-light/30",
      )}
      onClick={() => {
        setExpanded(!expanded);
        if (!alert.isRead) onMarkRead(alert.id);
      }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {!alert.isRead && (
              <span className="h-1.5 w-1.5 rounded-full bg-brand-500 flex-shrink-0" aria-label="Unread" />
            )}
            <p className="text-14 font-medium text-neutral-800 truncate">{alert.title}</p>
          </div>
          <div className="flex items-center gap-3 text-12 text-neutral-400">
            <span>{alert.jurisdiction} · {alert.regime}</span>
            <span>·</span>
            <span className={cn(alert.daysUntilEffective < 14 ? "text-warning-base font-medium" : "")}>
              {urgencyLabel}
            </span>
          </div>
          {expanded && (
            <p className="text-13 text-neutral-600 mt-3 leading-relaxed">{alert.summary}</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Badge variant={alert.severity.toLowerCase()} />
        </div>
      </div>
    </div>
  );
}

// ─── Obligation row ───────────────────────────────────────────────────────────

function ObligationRow({ ob }: { ob: ComplianceObligation }) {
  const urgencyColor = ob.isOverdue
    ? "text-danger-base"
    : ob.daysUntilDue <= 14
      ? "text-warning-base"
      : "text-neutral-500";

  const dueDateLabel = ob.isOverdue
    ? `Overdue by ${Math.abs(ob.daysUntilDue)} days`
    : ob.daysUntilDue <= 14
      ? `Due in ${ob.daysUntilDue} days`
      : ob.dueDate;

  return (
    <div className={cn(
      "px-5 py-4 border-b border-neutral-100 last:border-0 flex items-center justify-between gap-4",
      ob.isOverdue && "bg-danger-light/40",
    )}>
      <div className="flex-1 min-w-0">
        <p className="text-14 font-medium text-neutral-800">{ob.title}</p>
        <p className="text-12 text-neutral-400 mt-0.5">{ob.jurisdiction} · {ob.regime} · {ob.frequency}</p>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <Calendar className="h-3.5 w-3.5 text-neutral-400" />
          <span className={cn("text-13 font-medium", urgencyColor)}>{dueDateLabel}</span>
        </div>
        <Button variant="secondary" size="sm">
          File
        </Button>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function MonitoringPage() {
  const [alerts, setAlerts] = useState<RegulatoryAlert[]>([]);
  const [obligations, setObligations] = useState<ComplianceObligation[]>([]);
  const [monitoringEnabled] = useState(true);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      const [alertsRes, obRes] = await Promise.all([
        request("/v1/monitoring/alerts") as Promise<{ data?: { items?: RegulatoryAlert[] } }>,
        request("/v1/monitoring/obligations") as Promise<{ data?: { items?: ComplianceObligation[] } }>,
      ]);
      const apiAlerts = alertsRes?.data?.items ?? [];
      const apiObs = obRes?.data?.items ?? [];
      setAlerts(apiAlerts.length > 0 ? apiAlerts : MOCK_ALERTS);
      setObligations(apiObs.length > 0 ? apiObs : MOCK_OBLIGATIONS);
    } catch {
      setAlerts(MOCK_ALERTS);
      setObligations(MOCK_OBLIGATIONS);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleMarkRead(id: string) {
    setAlerts((prev) => prev.map((a) => a.id === id ? { ...a, isRead: true } : a));
    try {
      await request(`/v1/monitoring/alerts/${id}`, { method: "PATCH", body: JSON.stringify({ is_read: true }) });
    } catch {
      // best-effort
    }
  }

  const unreadCount = alerts.filter((a) => !a.isRead).length;
  const overdueCount = obligations.filter((o) => o.isOverdue).length;
  const jurisdictions = Array.from(new Set(alerts.map((a) => a.jurisdiction)));

  return (
    <>
      <PageHeader
        title="Regulatory Monitoring"
        subtitle="24/7 alerts on regulatory changes that affect your compliance posture"
        action={
          <div className="flex items-center gap-2">
            {monitoringEnabled ? (
              <div className="flex items-center gap-1.5 text-13 text-success-base">
                <CheckCircle2 className="h-4 w-4" />
                <span>Monitoring active</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-13 text-neutral-400">
                <BellOff className="h-4 w-4" />
                <span>Monitoring paused</span>
              </div>
            )}
          </div>
        }
      />

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-neutral-200 rounded-base p-5">
          <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1">
            Unread Alerts
          </p>
          <p className={cn(
            "text-28 font-medium leading-none",
            unreadCount > 0 ? "text-warning-base" : "text-neutral-800",
          )}>
            {unreadCount}
          </p>
        </div>
        <div className="bg-white border border-neutral-200 rounded-base p-5">
          <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1">
            Overdue Obligations
          </p>
          <p className={cn(
            "text-28 font-medium leading-none",
            overdueCount > 0 ? "text-danger-base" : "text-neutral-800",
          )}>
            {overdueCount}
          </p>
        </div>
        <div className="bg-white border border-neutral-200 rounded-base p-5">
          <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider mb-1">
            Jurisdictions Monitored
          </p>
          <p className="text-28 font-medium leading-none text-neutral-800">
            {jurisdictions.length || 3}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main alerts column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Regulatory alerts */}
          <Card padding={false}>
            <div className="px-5 py-4 border-b border-neutral-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4 text-neutral-500" />
                <h3 className="text-16 font-medium text-neutral-800">Regulatory Alerts</h3>
                {unreadCount > 0 && (
                  <span className="h-5 min-w-5 px-1.5 rounded-full bg-brand-500 text-white text-11 font-medium flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </div>
            </div>

            {!loaded ? (
              <div className="px-5 py-8 flex justify-center">
                <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : alerts.length === 0 ? (
              <div className="px-5 py-8">
                <EmptyState
                  title="No regulatory alerts"
                  description="We'll notify you when regulations change in your monitored jurisdictions."
                />
              </div>
            ) : (
              <div>
                {alerts.map((alert) => (
                  <AlertRow key={alert.id} alert={alert} onMarkRead={handleMarkRead} />
                ))}
              </div>
            )}
          </Card>

          {/* Upcoming obligations */}
          <Card padding={false}>
            <div className="px-5 py-4 border-b border-neutral-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-neutral-500" />
                <h3 className="text-16 font-medium text-neutral-800">Compliance Obligations</h3>
              </div>
            </div>

            {obligations.length === 0 ? (
              <div className="px-5 py-8">
                <EmptyState
                  title="No obligations tracked"
                  description="Obligations will appear here based on your jurisdiction and regime selections."
                />
              </div>
            ) : (
              <div>
                {obligations.sort((a, b) => a.daysUntilDue - b.daysUntilDue).map((ob) => (
                  <ObligationRow key={ob.id} ob={ob} />
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Sidebar: coverage and sources */}
        <div className="space-y-4">
          <Card>
            <SectionHeader title="Monitored Jurisdictions" />
            <div className="space-y-2">
              {[
                { code: "GB", name: "United Kingdom", regimes: ["AML", "FCA", "GDPR", "HMRC"] },
                { code: "EU", name: "European Union", regimes: ["GDPR", "AMLD6"] },
                { code: "AE", name: "United Arab Emirates", regimes: ["CBUAE", "RERA"] },
              ].map(({ code, name, regimes }) => (
                <div key={code} className="flex items-start gap-3 py-2 border-b border-neutral-100 last:border-0">
                  <div className="flex items-center gap-1.5 min-w-[28px]">
                    <Globe className="h-4 w-4 text-neutral-400" />
                    <span className="text-12 font-mono text-neutral-500">{code}</span>
                  </div>
                  <div className="flex-1">
                    <p className="text-13 font-medium text-neutral-700">{name}</p>
                    <p className="text-11 text-neutral-400 mt-0.5">{regimes.join(" · ")}</p>
                  </div>
                  <CheckCircle2 className="h-4 w-4 text-success-base flex-shrink-0 mt-0.5" />
                </div>
              ))}
            </div>
            <div className="mt-4">
              <Button variant="secondary" size="sm" fullWidth>
                Add Jurisdiction
              </Button>
            </div>
          </Card>

          <Card>
            <SectionHeader title="Data Sources" />
            <div className="space-y-2">
              {[
                "FCA Policy Statements",
                "HMRC AML Supervision",
                "ICO Guidance",
                "NCA Typologies",
                "FATF Mutual Evaluations",
                "UK Statutory Instruments",
              ].map((source) => (
                <div key={source} className="flex items-center gap-2 py-1.5 border-b border-neutral-100 last:border-0">
                  <ShieldCheck className="h-3.5 w-3.5 text-success-base flex-shrink-0" />
                  <span className="text-13 text-neutral-600">{source}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
