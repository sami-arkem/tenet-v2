"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  ClipboardCheck,
  FileSearch,
  Wrench,
  LogOut,
  Shield,
} from "lucide-react";

const NAV = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    matchPrefix: "/dashboard",
    exact: true,
  },
  {
    href: "/audits",
    label: "Audits",
    icon: ClipboardCheck,
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
    icon: Wrench,
    matchPrefix: "/remediation",
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { userId, logout } = useAuth();

  return (
    <aside className="w-56 flex-none flex flex-col border-r border-neutral-200 bg-white h-full">
      {/* Wordmark */}
      <div className="px-5 py-5 border-b border-neutral-200">
        <div className="flex items-center gap-2">
          <Shield size={16} className="text-brand-500" />
          <span className="text-14 font-medium tracking-tight text-neutral-800">
            Tenet
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-0.5" aria-label="Main navigation">
        {NAV.map(({ href, label, icon: Icon, matchPrefix, exact }) => {
          const active = exact
            ? pathname === href
            : pathname === href || pathname.startsWith(matchPrefix + "/");
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "relative flex items-center gap-2.5 px-3 py-2 rounded-base text-14 transition-colors duration-base",
                active
                  ? "bg-brand-50 text-brand-600 font-medium"
                  : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-800",
              )}
            >
              {/* Bible §T.2.2: 2px left indicator on active item */}
              {active && (
                <span
                  className="absolute left-0 top-1 bottom-1 w-0.5 bg-brand-500 rounded-full"
                  aria-hidden="true"
                />
              )}
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User / Sign-out */}
      <div className="px-4 py-4 border-t border-neutral-200">
        <div className="text-12 text-neutral-400 mb-2 truncate font-mono">
          {userId}
        </div>
        <button
          onClick={logout}
          className={cn(
            "flex items-center gap-2 text-13 text-neutral-500",
            "hover:text-neutral-700 transition-colors duration-base",
          )}
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
