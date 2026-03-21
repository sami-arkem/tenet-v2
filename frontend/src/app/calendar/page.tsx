// Compliance Calendar — Bible §3.15
// Shows upcoming compliance obligations, filing deadlines, audit schedules
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { request } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/utils";
import {
  ChevronLeft,
  ChevronRight,
  Calendar,
  AlertTriangle,
  FileText,
  ClipboardCheck,
  Plus,
} from "lucide-react";

type EventType = "audit" | "filing" | "obligation" | "review";
type EventSeverity = "critical" | "high" | "medium" | "low";

interface CalendarEvent {
  id: string;
  date: string;          // YYYY-MM-DD
  title: string;
  type: EventType;
  severity: EventSeverity;
  regime: string;
  jurisdiction: string;
  isOverdue: boolean;
}

// Static placeholder — used as fallback when API returns no results
const MOCK_EVENTS: CalendarEvent[] = [
  {
    id: "ev-001",
    date: "2025-04-05",
    title: "Quarterly AML Training Review",
    type: "obligation",
    severity: "medium",
    regime: "AML",
    jurisdiction: "GB",
    isOverdue: false,
  },
  {
    id: "ev-002",
    date: "2025-04-15",
    title: "FCA REP-CRIM Annual Submission",
    type: "filing",
    severity: "high",
    regime: "FCA",
    jurisdiction: "GB",
    isOverdue: false,
  },
  {
    id: "ev-003",
    date: "2025-04-20",
    title: "Scheduled AML Audit",
    type: "audit",
    severity: "medium",
    regime: "AML",
    jurisdiction: "GB",
    isOverdue: false,
  },
  {
    id: "ev-004",
    date: "2025-03-31",
    title: "ICO Annual Registration Renewal",
    type: "filing",
    severity: "critical",
    regime: "GDPR",
    jurisdiction: "GB",
    isOverdue: true,
  },
  {
    id: "ev-005",
    date: "2025-05-01",
    title: "Annual AML Policy Review",
    type: "obligation",
    severity: "high",
    regime: "AML",
    jurisdiction: "GB",
    isOverdue: false,
  },
  {
    id: "ev-006",
    date: "2025-05-31",
    title: "HMRC Supervision Fee Payment",
    type: "filing",
    severity: "high",
    regime: "AML",
    jurisdiction: "GB",
    isOverdue: false,
  },
  {
    id: "ev-007",
    date: "2025-06-30",
    title: "H1 Compliance Board Report",
    type: "review",
    severity: "medium",
    regime: "FCA",
    jurisdiction: "GB",
    isOverdue: false,
  },
];

const TYPE_ICON: Record<EventType, React.ComponentType<{ className?: string }>> = {
  audit: ClipboardCheck,
  filing: FileText,
  obligation: AlertTriangle,
  review: Calendar,
};

const TYPE_LABEL: Record<EventType, string> = {
  audit: "Audit",
  filing: "Filing",
  obligation: "Obligation",
  review: "Review",
};

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const TODAY = new Date();

function EventCard({ event }: { event: CalendarEvent }) {
  const router = useRouter();
  const Icon = TYPE_ICON[event.type];
  const isUrgent = event.isOverdue || (
    !event.isOverdue &&
    new Date(event.date) <= new Date(Date.now() + 14 * 24 * 60 * 60 * 1000)
  );

  return (
    <div
      className={cn(
        "flex items-start gap-3 px-4 py-3 border-b border-neutral-100 last:border-0",
        "hover:bg-neutral-50 transition-colors duration-base cursor-pointer",
        event.isOverdue && "bg-danger-light/30",
      )}
      onClick={() => {
        if (event.type === "audit") router.push("/audits/new");
        else if (event.type === "filing") router.push("/monitoring");
      }}
    >
      <div className={cn(
        "p-1.5 rounded-base flex-shrink-0 mt-0.5",
        event.isOverdue ? "bg-danger-light text-danger-base" :
        isUrgent ? "bg-warning-light text-warning-base" :
        "bg-neutral-100 text-neutral-500",
      )}>
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className={cn(
          "text-13 font-medium",
          event.isOverdue ? "text-danger-dark" : "text-neutral-800",
        )}>
          {event.title}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-11 text-neutral-400">{event.regime} · {event.jurisdiction}</span>
          <span className="text-11 text-neutral-300">·</span>
          <span className={cn(
            "text-11 font-medium",
            event.isOverdue ? "text-danger-base" : isUrgent ? "text-warning-base" : "text-neutral-400",
          )}>
            {event.isOverdue ? "Overdue" : event.date}
          </span>
        </div>
      </div>
      <Badge variant={event.severity} />
    </div>
  );
}

function MonthCalendar({
  year,
  month,
  events,
  onDayClick,
  selectedDay,
}: {
  year: number;
  month: number;
  events: CalendarEvent[];
  onDayClick: (day: number) => void;
  selectedDay: number | null;
}) {
  const firstDay = new Date(year, month, 1).getDay(); // 0=Sun
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const blanks = Array.from({ length: firstDay });
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);

  const eventsByDay = events.reduce<Record<number, CalendarEvent[]>>((acc, ev) => {
    const d = new Date(ev.date);
    if (d.getFullYear() === year && d.getMonth() === month) {
      const day = d.getDate();
      acc[day] = [...(acc[day] ?? []), ev];
    }
    return acc;
  }, {});

  const isToday = (day: number) =>
    TODAY.getFullYear() === year && TODAY.getMonth() === month && TODAY.getDate() === day;

  return (
    <div>
      <div className="grid grid-cols-7 mb-1">
        {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((d) => (
          <div key={d} className="py-1 text-center text-11 font-medium text-neutral-400 uppercase tracking-wider">
            {d}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7">
        {blanks.map((_, i) => (
          <div key={`blank-${i}`} />
        ))}
        {days.map((day) => {
          const dayEvents = eventsByDay[day] ?? [];
          const hasOverdue = dayEvents.some((e) => e.isOverdue);
          const hasHigh = dayEvents.some((e) => e.severity === "high" || e.severity === "critical");
          const isSelected = selectedDay === day;

          return (
            <button
              key={day}
              onClick={() => onDayClick(day)}
              className={cn(
                "relative h-9 rounded-base text-14 transition-colors duration-base",
                isSelected ? "bg-brand-500 text-white" :
                isToday(day) ? "bg-brand-50 text-brand-600 font-medium" :
                dayEvents.length > 0 ? "hover:bg-neutral-100 text-neutral-800" :
                "hover:bg-neutral-50 text-neutral-500",
              )}
            >
              {day}
              {dayEvents.length > 0 && !isSelected && (
                <span
                  className={cn(
                    "absolute bottom-1 left-1/2 -translate-x-1/2 h-1 w-1 rounded-full",
                    hasOverdue ? "bg-danger-base" : hasHigh ? "bg-warning-base" : "bg-brand-400",
                  )}
                />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(() => new Date(TODAY.getFullYear(), TODAY.getMonth(), 1));
  const [selectedDay, setSelectedDay] = useState<number | null>(TODAY.getDate());
  const [events, setEvents] = useState<CalendarEvent[]>(MOCK_EVENTS);

  const load = useCallback(async () => {
    try {
      const today = new Date();
      const from = new Date(today.getFullYear(), today.getMonth() - 1, 1).toISOString().split("T")[0];
      const to = new Date(today.getFullYear(), today.getMonth() + 3, 0).toISOString().split("T")[0];
      const res = await request<{ events?: CalendarEvent[] } | CalendarEvent[]>(`/v1/calendar/events?from=${from}&to=${to}`);
      const apiEvents = Array.isArray(res) ? res : (res as any)?.events ?? [];
      if (apiEvents.length > 0) setEvents(apiEvents);
    } catch {
      // keep mock data
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const prevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(year, month + 1, 1));

  const upcomingEvents = events.filter((e) => {
    const d = new Date(e.date);
    return d >= new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  }).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  const selectedDayEvents = selectedDay
    ? events.filter((e) => {
        const d = new Date(e.date);
        return d.getFullYear() === year && d.getMonth() === month && d.getDate() === selectedDay;
      })
    : [];

  const overdueEvents = events.filter((e) => e.isOverdue);

  return (
    <>
      <PageHeader
        title="Compliance Calendar"
        subtitle="Upcoming obligations, filing deadlines, and scheduled audits"
        action={
          <Button variant="primary" size="sm" iconLeft={<Plus />}>
            Add Obligation
          </Button>
        }
      />

      {overdueEvents.length > 0 && (
        <div className="flex items-center gap-3 px-5 py-4 rounded-base border border-danger-base bg-danger-light mb-6">
          <AlertTriangle className="h-5 w-5 text-danger-base flex-shrink-0" />
          <p className="text-14 font-medium text-danger-dark">
            {overdueEvents.length} overdue obligation{overdueEvents.length !== 1 ? "s" : ""} require immediate attention
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar widget */}
        <div className="lg:col-span-1 space-y-4">
          <Card>
            {/* Month navigation */}
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={prevMonth}
                className="p-1 rounded-base hover:bg-neutral-100 transition-colors duration-base"
                aria-label="Previous month"
              >
                <ChevronLeft className="h-4 w-4 text-neutral-500" />
              </button>
              <span className="text-14 font-medium text-neutral-800">
                {MONTHS[month]} {year}
              </span>
              <button
                onClick={nextMonth}
                className="p-1 rounded-base hover:bg-neutral-100 transition-colors duration-base"
                aria-label="Next month"
              >
                <ChevronRight className="h-4 w-4 text-neutral-500" />
              </button>
            </div>

            <MonthCalendar
              year={year}
              month={month}
              events={events}
              onDayClick={setSelectedDay}
              selectedDay={selectedDay}
            />
          </Card>

          {/* Selected day events */}
          {selectedDay && (
            <Card padding={false}>
              <div className="px-4 py-3 border-b border-neutral-200">
                <p className="text-13 font-medium text-neutral-700">
                  {MONTHS[month]} {selectedDay}, {year}
                </p>
              </div>
              {selectedDayEvents.length === 0 ? (
                <div className="px-4 py-6 text-center">
                  <p className="text-13 text-neutral-400">No events on this day</p>
                </div>
              ) : (
                selectedDayEvents.map((ev) => (
                  <EventCard key={ev.id} event={ev} />
                ))
              )}
            </Card>
          )}
        </div>

        {/* Upcoming events list */}
        <div className="lg:col-span-2">
          <Card padding={false}>
            <div className="px-5 py-4 border-b border-neutral-200 flex items-center justify-between">
              <h3 className="text-16 font-medium text-neutral-800">Upcoming Events</h3>
              <p className="text-13 text-neutral-400">{upcomingEvents.length} events</p>
            </div>

            {upcomingEvents.length === 0 ? (
              <div className="px-5 py-8">
                <EmptyState
                  title="No upcoming events"
                  description="Add compliance obligations or connect to a filing schedule to see events here."
                />
              </div>
            ) : (
              <div>
                {/* Group by month */}
                {["2025-03", "2025-04", "2025-05", "2025-06"].map((monthKey) => {
                  const [y, m] = monthKey.split("-").map(Number);
                  const monthEvents = upcomingEvents.filter((e) => e.date.startsWith(monthKey));
                  if (monthEvents.length === 0) return null;
                  return (
                    <div key={monthKey}>
                      <div className="px-5 py-2 bg-neutral-50 border-b border-neutral-100">
                        <p className="text-11 font-medium text-neutral-500 uppercase tracking-wider">
                          {MONTHS[m - 1]} {y}
                        </p>
                      </div>
                      {monthEvents.map((ev) => (
                        <EventCard key={ev.id} event={ev} />
                      ))}
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
