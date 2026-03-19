"use client";

import { useAuth } from "@/contexts/AuthContext";
import { Sidebar } from "./Sidebar";
import { LoginGate } from "./LoginGate";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <LoginGate />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-subtle">
      <Sidebar />
      <main className="flex-1 overflow-y-auto min-w-0">
        <div className="max-w-content mx-auto px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
