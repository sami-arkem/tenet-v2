"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";
import {
  LayoutList,
  ClipboardCheck,
  FileSearch,
  AlertTriangle,
  BarChart2,
  CheckSquare,
  LogOut,
  ShieldCheck,
} from "lucide-react";

const NAV = [
  {
    href: "/audits",
    label: "Audits",
    icon: LayoutList,
    matchPrefix: "/audits",
  },
  {
    href: "/evidence-review",
    label: "Evidence Review",
    icon: FileSearch,
    matchPrefix: "/evidence-review",
  },
  {
    href: "/remediation",
    label: "Remediation",
    icon: CheckSquare,
    matchPrefix: "/remediation",
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { userId, logout } = useAuth();

  return (
    <aside className="w-56 flex-none flex flex-col border-r border-surface-border bg-surface h-full">
      {/* Wordmark */}
      <div className="px-5 py-5 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <ShieldCheck size={16} className="text-text-secondary" />
          <span className="text-sm font-semibold tracking-tight">Tenet</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon, matchPrefix }) => {
          const active =
            pathname === href || pathname.startsWith(matchPrefix + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded text-sm transition-fast",
                active
                  ? "bg-surface-muted text-text font-medium"
                  : "text-text-secondary hover:bg-surface-subtle hover:text-text",
              )}
            >
              <Icon size={15} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User / Sign-out */}
      <div className="px-4 py-4 border-t border-surface-border">
        <div className="text-xs text-text-muted mb-2 truncate mono">
          {userId}
        </div>
        <button
          onClick={logout}
          className="
            flex items-center gap-2 text-xs text-text-secondary
            hover:text-text transition-fast
          "
        >
          <LogOut size={13} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
