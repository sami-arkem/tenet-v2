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
        className="relative z-10 bg-white border border-neutral-200 rounded-lg shadow-base w-full max-w-sm mx-4 p-5"
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <h2 id="modal-title" className="text-14 font-semibold text-neutral-900">
            {title}
          </h2>
          <button
            onClick={onCancel}
            className="text-neutral-400 hover:text-neutral-700 transition-colors duration-base flex-none"
            aria-label="Close"
          >
            <X size={14} />
          </button>
        </div>

        {description && (
          <p className="text-14 text-neutral-500 mb-4">{description}</p>
        )}

        {children && <div className="mb-4">{children}</div>}

        <div className="flex items-center justify-end gap-2.5">
          <button
            onClick={onCancel}
            className="
              px-3 py-1.5 text-14 text-neutral-500 border border-neutral-200
              rounded-base hover:bg-neutral-50 transition-colors duration-base
            "
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={cn(
              "px-3 py-1.5 text-14 rounded-base transition-colors duration-base font-medium",
              destructive
                ? "bg-danger-base text-white hover:bg-danger-dark"
                : "bg-brand-500 text-white hover:bg-brand-600",
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
