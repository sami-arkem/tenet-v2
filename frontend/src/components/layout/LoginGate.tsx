"use client";

import { useState } from "react";
import { Shield } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

type Mode = "login" | "signup";

interface ApiError {
  code: string;
  message: string;
}

const BASE = "/api/proxy";

async function apiPost<T>(path: string, body: object): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!res.ok || json.error) {
    const err: ApiError = json.error ?? { code: "ERROR", message: `HTTP ${res.status}` };
    throw err;
  }
  return json.data as T;
}

interface TokenResponse {
  access_token: string;
  expires_in: number;
  user_id: string;
  tenant_id: string;
  role: string;
}

export function LoginGate() {
  const { loginWithToken, login } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  function clearErrors() {
    setError(null);
    setFieldErrors({});
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    clearErrors();

    if (!email) {
      setFieldErrors({ email: "Email is required" });
      return;
    }
    if (!password) {
      setFieldErrors({ password: "Password is required" });
      return;
    }
    if (mode === "signup" && !fullName) {
      setFieldErrors({ fullName: "Full name is required" });
      return;
    }

    setLoading(true);
    try {
      if (mode === "login") {
        const data = await apiPost<TokenResponse>("/v1/auth/login", { email, password });
        loginWithToken(data.access_token, {
          userId: data.user_id,
          tenantId: data.tenant_id,
          role: data.role,
        });
      } else {
        const data = await apiPost<TokenResponse>("/v1/auth/signup", {
          email,
          password,
          full_name: fullName,
        });
        loginWithToken(data.access_token, {
          userId: data.user_id,
          tenantId: data.tenant_id,
          role: data.role,
        });
      }
    } catch (err) {
      const apiErr = err as ApiError;
      if (apiErr.code === "PASSWORD_TOO_WEAK") {
        setFieldErrors({ password: apiErr.message });
      } else if (apiErr.code === "EMAIL_TAKEN") {
        setFieldErrors({ email: "An account with this email already exists" });
      } else if (apiErr.code === "INVALID_CREDENTIALS") {
        setError("Incorrect email or password");
      } else {
        setError(apiErr.message ?? "Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  // Dev fallback: if no backend, allow direct user ID login
  function handleDevLogin(e: React.FormEvent) {
    e.preventDefault();
    if (email.trim()) login(email.trim());
  }

  return (
    <div className="min-h-screen bg-neutral-50 flex">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-[480px] bg-neutral-900 flex-col justify-between p-10">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center w-8 h-8 rounded-md bg-brand-600">
            <Shield size={16} className="text-white" />
          </div>
          <span className="text-18 font-semibold text-white tracking-tight">Tenet</span>
        </div>
        <div>
          <h1 className="text-28 font-semibold text-white leading-tight mb-3">
            AI Compliance<br />Operating System
          </h1>
          <p className="text-15 text-neutral-400 max-w-xs leading-relaxed">
            Automated regulatory audits, real-time monitoring, and deployment governance for AI systems.
          </p>
        </div>
        <p className="text-12 text-neutral-600">
          Multi-jurisdiction compliance coverage
        </p>
      </div>
      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        {/* Mobile-only wordmark */}
        <div className="mb-10 lg:hidden flex flex-col gap-1">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-7 h-7 rounded-md bg-brand-600">
              <Shield size={14} className="text-white" />
            </div>
            <span className="text-20 font-semibold text-neutral-900 tracking-tight">Tenet</span>
          </div>
          <p className="text-14 text-neutral-500 pl-[38px]">
            Compliance operating system
          </p>
        </div>
        {/* Desktop heading */}
        <div className="hidden lg:block mb-8">
          <h2 className="text-22 font-semibold text-neutral-900">Welcome back</h2>
          <p className="text-14 text-neutral-500 mt-1">Sign in to your compliance workspace</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "signup" && (
            <Input
              label="Full name"
              type="text"
              autoComplete="name"
              autoFocus
              value={fullName}
              onChange={(e) => { setFullName(e.target.value); clearErrors(); }}
              placeholder="Jane Smith"
              error={fieldErrors.fullName}
              required
            />
          )}

          <Input
            label="Email"
            type="email"
            autoComplete="email"
            autoFocus={mode === "login"}
            value={email}
            onChange={(e) => { setEmail(e.target.value); clearErrors(); }}
            placeholder="you@company.com"
            error={fieldErrors.email}
            required
          />

          <Input
            label="Password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => { setPassword(e.target.value); clearErrors(); }}
            placeholder={mode === "signup" ? "Min. 12 characters" : "••••••••••••"}
            error={fieldErrors.password}
            helpText={mode === "signup" ? "Min. 12 chars, uppercase, number, special character" : undefined}
            required
          />

          {error && (
            <p className="text-13 text-danger-dark" role="alert">
              {error}
            </p>
          )}

          <Button
            type="submit"
            variant="primary"
            fullWidth
            loading={loading}
          >
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>

        <p className="mt-6 text-13 text-neutral-500 text-center">
          {mode === "login" ? (
            <>
              No account?{" "}
              <button
                className="text-brand-600 hover:underline font-medium"
                onClick={() => { setMode("signup"); clearErrors(); }}
              >
                Create one
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button
                className="text-brand-600 hover:underline font-medium"
                onClick={() => { setMode("login"); clearErrors(); }}
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
      </div>
    </div>
  );
}
