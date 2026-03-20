"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { request } from "@/lib/api";
import { Sidebar } from "./Sidebar";
import { LoginGate } from "./LoginGate";
import { OnboardingWizard } from "./OnboardingWizard";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [onboardingDone, setOnboardingDone] = useState<boolean | null>(null);

  const checkEntities = useCallback(async () => {
    try {
      const data = await request("/v1/entities?limit=1") as { data?: { total?: number } };
      setOnboardingDone((data?.data?.total ?? 0) > 0);
    } catch {
      // On error (e.g. auth failure before entity check), skip onboarding
      setOnboardingDone(true);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      checkEntities();
    }
  }, [isAuthenticated, checkEntities]);

  if (!isAuthenticated) {
    return <LoginGate />;
  }

  if (onboardingDone === null) {
    return (
      <div className="flex h-screen items-center justify-center bg-neutral-50">
        <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!onboardingDone) {
    return <OnboardingWizard onComplete={() => setOnboardingDone(true)} />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-neutral-50">
      <Sidebar />
      <main className="flex-1 overflow-y-auto min-w-0">
        <div className="max-w-content mx-auto px-10 py-8">{children}</div>
      </main>
    </div>
  );
}
