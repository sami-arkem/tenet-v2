"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

export function LoginGate() {
  const { login } = useAuth();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) {
      setError("User ID is required.");
      return;
    }
    login(trimmed);
  }

  return (
    <div className="min-h-screen bg-surface-subtle flex items-center justify-center">
      <div className="w-full max-w-sm">
        {/* Wordmark */}
        <div className="mb-10">
          <span className="text-lg font-semibold tracking-tight text-text">
            Tenet
          </span>
          <p className="mt-1 text-text-secondary text-sm">
            Compliance operating system
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="user-id"
              className="block text-xs font-medium text-text-secondary uppercase tracking-wide mb-1.5"
            >
              User ID
            </label>
            <input
              id="user-id"
              type="text"
              autoComplete="off"
              autoFocus
              value={value}
              onChange={(e) => {
                setValue(e.target.value);
                setError(null);
              }}
              placeholder="e.g. user_alice"
              className="
                w-full px-3 py-2
                border border-surface-border rounded
                bg-surface text-text text-sm
                placeholder:text-text-muted
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                transition-fast
              "
            />
            {error && (
              <p className="mt-1.5 text-xs text-red-600">{error}</p>
            )}
          </div>

          <button
            type="submit"
            className="
              w-full px-4 py-2
              bg-text text-surface text-sm font-medium rounded
              hover:bg-zinc-700
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
              transition-fast
            "
          >
            Sign in
          </button>
        </form>

        <p className="mt-6 text-xs text-text-muted">
          Operator access only. User ID must exist in the actor directory.
        </p>
      </div>
    </div>
  );
}
