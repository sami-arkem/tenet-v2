"use client";

/**
 * OnboardingWizard — Bible §5 / onboarding flow.
 * 5-step wizard shown after first login when no entities exist.
 * Creates a regulated entity and completes tenant configuration.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, Shield, Globe, Users, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { request } from "@/lib/api";

// ─── Step types ───────────────────────────────────────────────────────────────

interface WizardState {
  // Step 1: Company basics
  companyName: string;
  entityType: "company" | "ai_system" | "department" | "product";
  // Step 2: Jurisdiction
  jurisdiction: string;
  // Step 3: Industry & size
  industrySector: string;
  companySize: "micro" | "small" | "medium" | "large" | "enterprise" | "";
  // Step 4: Regulatory regimes
  regimes: string[];
}

const INITIAL_STATE: WizardState = {
  companyName: "",
  entityType: "company",
  jurisdiction: "GB",
  industrySector: "",
  companySize: "",
  regimes: ["AML"],
};

const STEPS = [
  { id: 1, label: "Company", icon: Building2 },
  { id: 2, label: "Location", icon: Globe },
  { id: 3, label: "Profile", icon: Users },
  { id: 4, label: "Regimes", icon: Shield },
  { id: 5, label: "Done", icon: CheckCircle2 },
];

const ENTITY_TYPES = [
  { value: "company", label: "Company / Group" },
  { value: "ai_system", label: "AI System" },
  { value: "department", label: "Department" },
  { value: "product", label: "Product" },
] as const;

const JURISDICTIONS = [
  { value: "GB", label: "United Kingdom" },
  { value: "US", label: "United States" },
  { value: "EU", label: "European Union" },
  { value: "AE", label: "UAE" },
  { value: "SG", label: "Singapore" },
  { value: "HK", label: "Hong Kong" },
  { value: "AU", label: "Australia" },
  { value: "CA", label: "Canada" },
];

const COMPANY_SIZES = [
  { value: "micro", label: "Micro (1–9 employees)" },
  { value: "small", label: "Small (10–49 employees)" },
  { value: "medium", label: "Medium (50–249 employees)" },
  { value: "large", label: "Large (250–999 employees)" },
  { value: "enterprise", label: "Enterprise (1,000+)" },
] as const;

const ALL_REGIMES = [
  { value: "AML", label: "Anti-Money Laundering (AML)", description: "POCA 2002, MLR 2017" },
  { value: "GDPR", label: "GDPR / Data Protection", description: "UK GDPR, EU GDPR" },
  { value: "FCA", label: "FCA (Financial Services)", description: "SYSC, SMCR, Consumer Duty" },
  { value: "SANCTIONS", label: "Sanctions Compliance", description: "OFAC, OFSI, UN" },
];

// ─── Step components ──────────────────────────────────────────────────────────

function StepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex items-center gap-0 mb-10">
      {STEPS.map((step, idx) => {
        const isComplete = step.id < currentStep;
        const isCurrent = step.id === currentStep;
        const Icon = step.icon;
        return (
          <div key={step.id} className="flex items-center">
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={[
                  "w-9 h-9 rounded-full flex items-center justify-center transition-colors",
                  isComplete
                    ? "bg-brand-500 text-white"
                    : isCurrent
                    ? "bg-brand-50 border-2 border-brand-500 text-brand-600"
                    : "bg-neutral-100 border border-neutral-200 text-neutral-400",
                ].join(" ")}
              >
                <Icon className="w-4 h-4" />
              </div>
              <span
                className={[
                  "text-11 font-medium whitespace-nowrap",
                  isCurrent ? "text-brand-600" : isComplete ? "text-brand-500" : "text-neutral-400",
                ].join(" ")}
              >
                {step.label}
              </span>
            </div>
            {idx < STEPS.length - 1 && (
              <div
                className={[
                  "h-0.5 w-12 mx-1 mt-[-14px] transition-colors",
                  isComplete ? "bg-brand-500" : "bg-neutral-200",
                ].join(" ")}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Main wizard ──────────────────────────────────────────────────────────────

interface OnboardingWizardProps {
  onComplete: () => void;
}

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState(1);
  const [state, setState] = useState<WizardState>(INITIAL_STATE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  function update<K extends keyof WizardState>(key: K, value: WizardState[K]) {
    setState((prev) => ({ ...prev, [key]: value }));
  }

  function toggleRegime(regime: string) {
    setState((prev) => ({
      ...prev,
      regimes: prev.regimes.includes(regime)
        ? prev.regimes.filter((r) => r !== regime)
        : [...prev.regimes, regime],
    }));
  }

  async function handleFinish() {
    setLoading(true);
    setError(null);
    try {
      await request("/v1/entities", {
        method: "POST",
        body: JSON.stringify({
          name: state.companyName,
          entity_type: state.entityType,
          jurisdiction: state.jurisdiction,
          industry_sector: state.industrySector || undefined,
          company_size: state.companySize || undefined,
          regulatory_regimes: state.regimes,
        }),
      });
      setStep(5);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create entity");
    } finally {
      setLoading(false);
    }
  }

  function handleDone() {
    onComplete();
    router.push("/dashboard");
  }

  return (
    <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-6">
      <div className="w-full max-w-lg bg-white rounded-xl border border-neutral-200 shadow-sm p-8">
        {/* Header */}
        <div className="mb-8">
          <p className="text-12 font-semibold tracking-widest text-brand-500 uppercase mb-1">
            TENET
          </p>
          <h1 className="text-20 font-semibold text-neutral-800">
            Set up your compliance workspace
          </h1>
          <p className="text-14 text-neutral-500 mt-1">
            Tell us about your organisation to configure the right controls.
          </p>
        </div>

        <StepIndicator currentStep={step} />

        {/* Steps */}
        {step === 1 && (
          <div className="space-y-5">
            <h2 className="text-16 font-semibold text-neutral-800">Organisation details</h2>
            <Input
              label="Organisation name"
              required
              value={state.companyName}
              onChange={(e) => update("companyName", e.target.value)}
              placeholder="Acme Financial Ltd"
            />
            <div className="flex flex-col gap-1.5">
              <label className="text-13 font-medium text-neutral-600">Entity type</label>
              <div className="grid grid-cols-2 gap-2">
                {ENTITY_TYPES.map((t) => (
                  <button
                    key={t.value}
                    onClick={() => update("entityType", t.value)}
                    className={[
                      "px-3 py-2.5 rounded-base border text-13 font-medium text-left transition-colors",
                      state.entityType === t.value
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-neutral-200 text-neutral-600 hover:border-neutral-300 hover:bg-neutral-50",
                    ].join(" ")}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <h2 className="text-16 font-semibold text-neutral-800">Primary jurisdiction</h2>
            <p className="text-13 text-neutral-500">
              Select the primary jurisdiction your organisation operates under.
            </p>
            <div className="grid grid-cols-2 gap-2">
              {JURISDICTIONS.map((j) => (
                <button
                  key={j.value}
                  onClick={() => update("jurisdiction", j.value)}
                  className={[
                    "px-3 py-2.5 rounded-base border text-13 font-medium text-left transition-colors",
                    state.jurisdiction === j.value
                      ? "border-brand-500 bg-brand-50 text-brand-700"
                      : "border-neutral-200 text-neutral-600 hover:border-neutral-300",
                  ].join(" ")}
                >
                  {j.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <h2 className="text-16 font-semibold text-neutral-800">Industry profile</h2>
            <Input
              label="Industry sector"
              value={state.industrySector}
              onChange={(e) => update("industrySector", e.target.value)}
              placeholder="e.g. Financial Services, FinTech, Payments"
            />
            <div className="flex flex-col gap-1.5">
              <label className="text-13 font-medium text-neutral-600">Organisation size</label>
              <div className="flex flex-col gap-1.5">
                {COMPANY_SIZES.map((s) => (
                  <button
                    key={s.value}
                    onClick={() => update("companySize", s.value)}
                    className={[
                      "px-3 py-2 rounded-base border text-13 font-medium text-left transition-colors",
                      state.companySize === s.value
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-neutral-200 text-neutral-600 hover:border-neutral-300",
                    ].join(" ")}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-5">
            <h2 className="text-16 font-semibold text-neutral-800">Regulatory regimes</h2>
            <p className="text-13 text-neutral-500">
              Select all regimes that apply. Tenet will configure the right controls.
            </p>
            <div className="flex flex-col gap-2">
              {ALL_REGIMES.map((r) => {
                const selected = state.regimes.includes(r.value);
                return (
                  <button
                    key={r.value}
                    onClick={() => toggleRegime(r.value)}
                    className={[
                      "px-4 py-3 rounded-base border text-left transition-colors",
                      selected
                        ? "border-brand-500 bg-brand-50"
                        : "border-neutral-200 hover:border-neutral-300",
                    ].join(" ")}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className={["text-13 font-medium", selected ? "text-brand-700" : "text-neutral-700"].join(" ")}>
                          {r.label}
                        </p>
                        <p className="text-12 text-neutral-400 mt-0.5">{r.description}</p>
                      </div>
                      <div
                        className={[
                          "w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 ml-4",
                          selected ? "border-brand-500 bg-brand-500" : "border-neutral-300",
                        ].join(" ")}
                      >
                        {selected && (
                          <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 12 12">
                            <path d="M10 3L5 8.5 2 5.5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
            {error && (
              <p className="text-12 text-danger-dark bg-danger-light px-3 py-2 rounded-base">
                {error}
              </p>
            )}
          </div>
        )}

        {step === 5 && (
          <div className="text-center space-y-4 py-4">
            <div className="w-14 h-14 rounded-full bg-brand-50 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-7 h-7 text-brand-500" />
            </div>
            <h2 className="text-18 font-semibold text-neutral-800">You&apos;re ready to go</h2>
            <p className="text-14 text-neutral-500">
              <strong className="text-neutral-700">{state.companyName}</strong> has been created with{" "}
              <strong className="text-neutral-700">{state.regimes.join(", ")}</strong> compliance controls.
            </p>
            <div className="flex flex-col gap-2 pt-2 text-13 text-neutral-500">
              <div className="flex items-center justify-between px-4 py-2 bg-neutral-50 rounded-base">
                <span>Jurisdiction</span>
                <span className="font-medium text-neutral-700">{state.jurisdiction}</span>
              </div>
              {state.industrySector && (
                <div className="flex items-center justify-between px-4 py-2 bg-neutral-50 rounded-base">
                  <span>Industry</span>
                  <span className="font-medium text-neutral-700">{state.industrySector}</span>
                </div>
              )}
              {state.companySize && (
                <div className="flex items-center justify-between px-4 py-2 bg-neutral-50 rounded-base">
                  <span>Size</span>
                  <span className="font-medium text-neutral-700 capitalize">{state.companySize}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between mt-8 pt-6 border-t border-neutral-100">
          {step > 1 && step < 5 ? (
            <Button variant="ghost" size="sm" onClick={() => setStep((s) => s - 1)}>
              Back
            </Button>
          ) : (
            <span />
          )}

          {step < 4 && (
            <Button
              size="md"
              onClick={() => setStep((s) => s + 1)}
              disabled={step === 1 && !state.companyName.trim()}
            >
              Continue
            </Button>
          )}

          {step === 4 && (
            <Button
              size="md"
              loading={loading}
              disabled={state.regimes.length === 0}
              onClick={handleFinish}
            >
              Create workspace
            </Button>
          )}

          {step === 5 && (
            <Button size="md" onClick={handleDone}>
              Go to dashboard
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
