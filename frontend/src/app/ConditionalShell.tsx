"use client";

import { usePathname } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";

const MARKETING_ROUTES = ["/landing"];

export function ConditionalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (MARKETING_ROUTES.some((r) => pathname === r || pathname.startsWith(r + "/"))) {
    return <>{children}</>;
  }
  return <AppShell>{children}</AppShell>;
}
