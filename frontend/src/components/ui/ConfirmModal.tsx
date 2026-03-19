"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ConfirmModalProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  children?: React.ReactNode;
}

export function ConfirmModal({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  onConfirm,
  onCancel,
  children,
}: ConfirmModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // Trap escape key
  useEffect(() => {
    if (!open) return;
    function handle(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        ref={dialogRef}
        className="relative z-10 bg-surface border border-surface-border rounded-lg shadow-md w-full max-w-sm mx-4 p-5"
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <h2 id="modal-title" className="text-sm font-semibold text-text">
            {title}
          </h2>
          <button
            onClick={onCancel}
            className="text-text-muted hover:text-text transition-fast flex-none"
            aria-label="Close"
          >
            <X size={14} />
          </button>
        </div>

        {description && (
          <p className="text-sm text-text-secondary mb-4">{description}</p>
        )}

        {children && <div className="mb-4">{children}</div>}

        <div className="flex items-center justify-end gap-2.5">
          <button
            onClick={onCancel}
            className="
              px-3 py-1.5 text-sm text-text-secondary border border-surface-border
              rounded hover:bg-surface-subtle transition-fast focus-ring
            "
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={cn(
              "px-3 py-1.5 text-sm rounded transition-fast focus-ring font-medium",
              destructive
                ? "bg-red-600 text-white hover:bg-red-700"
                : "bg-text text-surface hover:bg-zinc-700",
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
