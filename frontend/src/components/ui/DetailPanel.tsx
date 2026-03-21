// components/ui/DetailPanel.tsx — Bible §1.4.5
// Slide-in panel from right (480px). Used for findings, remediation detail, etc.
"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DetailPanelProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  width?: number;
}

export function DetailPanel({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  width = 480,
}: DetailPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) onClose();
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  // Focus panel when opened
  useEffect(() => {
    if (isOpen && panelRef.current) {
      panelRef.current.focus();
    }
  }, [isOpen]);

  return (
    <>
      {/* Click-away backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Slide-in panel — Bible: 250ms slideInRight */}
      <div
        ref={panelRef}
        role="complementary"
        aria-label="Detail panel"
        tabIndex={-1}
        style={{ width }}
        className={cn(
          "fixed right-0 top-0 bottom-0 z-40",
          "bg-white border-l border-neutral-200",
          "flex flex-col overflow-hidden",
          "transition-transform duration-slow ease-in-out",
          "focus:outline-none",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-neutral-100 shrink-0">
          <div className="flex-1 min-w-0 pr-4">
            <h2 className="text-16 font-medium text-neutral-800 truncate">
              {title}
            </h2>
            {subtitle && (
              <p className="mt-0.5 text-13 text-neutral-500">{subtitle}</p>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Close panel"
            className={cn(
              "flex items-center justify-center h-7 w-7 rounded-base",
              "text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100",
              "transition-colors duration-base focus:outline-none",
              "focus-visible:ring-2 focus-visible:ring-brand-500",
            )}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto">{children}</div>
      </div>
    </>
  );
}
