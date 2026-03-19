"use client";

import { useState } from "react";
import { Shield } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export function LoginGate() {
  const { login } = useAuth();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) {
      setError("User ID is required.");
      return;
    }
    setLoading(true);
    login(trimmed);
  }

  return (
    <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
      <div className="w-full max-w-sm">
        {/* Wordmark */}
        <div className="mb-10 flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <Shield size={18} className="text-brand-500" />
            <span className="text-20 font-medium text-neutral-900">
              Tenet
            </span>
          </div>
          <p className="text-14 text-neutral-500 pl-7">
            Compliance operating system
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <Input
            label="User ID"
            type="text"
            autoComplete="off"
            autoFocus
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setError(null);
            }}
            placeholder="e.g. user_alice"
            error={error ?? undefined}
            helpText="Must exist in the actor directory."
            required
          />

          <Button
            type="submit"
            variant="primary"
            fullWidth
            loading={loading}
          >
            Sign in
          </Button>
        </form>

        <p className="mt-6 text-12 text-neutral-400">
          Operator access only.
        </p>
      </div>
    </div>
  );
}
