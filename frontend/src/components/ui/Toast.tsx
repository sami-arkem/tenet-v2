// components/ui/Toast.tsx — Bible §1.4.6
// Rules: max 3 visible, success/info auto-dismiss 4s, warning 6s, error manual only
// Position: bottom-right, 24px from edge. slide-up 150ms.
"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
} from "react";
import { CheckCircle, XCircle, AlertTriangle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
}

interface ToastContextValue {
  toast: (opts: Omit<Toast, "id">) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const toastConfig: Record<
  ToastType,
  {
    icon: React.ComponentType<{ className?: string }>;
    className: string;
    iconClassName: string;
    duration: number | null; // null = manual dismiss only
  }
> = {
  success: {
    icon: CheckCircle,
    className: "border-l-4 border-l-success-base",
    iconClassName: "text-success-base",
    duration: 4000,
  },
  error: {
    icon: XCircle,
    className: "border-l-4 border-l-danger-base",
    iconClassName: "text-danger-base",
    duration: null, // manual dismiss only
  },
  warning: {
    icon: AlertTriangle,
    className: "border-l-4 border-l-warning-base",
    iconClassName: "text-warning-base",
    duration: 6000,
  },
  info: {
    icon: Info,
    className: "border-l-4 border-l-info-base",
    iconClassName: "text-info-base",
    duration: 4000,
  },
};

function ToastItem({
  toast: t,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: (id: string) => void;
}) {
  const config = toastConfig[t.type];
  const Icon = config.icon;
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (config.duration !== null) {
      timerRef.current = setTimeout(() => onDismiss(t.id), config.duration);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [t.id, config.duration, onDismiss]);

  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        "flex items-start gap-3 p-4 bg-white rounded-md shadow-md",
        "border border-neutral-200",
        "animate-in slide-in-from-bottom-2 duration-base",
        "min-w-[300px] max-w-[400px]",
        config.className,
      )}
    >
      <Icon className={cn("h-5 w-5 shrink-0 mt-0.5", config.iconClassName)} />
      <div className="flex-1 min-w-0">
        <p className="text-14 font-medium text-neutral-800">{t.title}</p>
        {t.description && (
          <p className="mt-1 text-13 text-neutral-500">{t.description}</p>
        )}
      </div>
      <button
        onClick={() => onDismiss(t.id)}
        aria-label="Dismiss notification"
        className={cn(
          "shrink-0 text-neutral-400 hover:text-neutral-600",
          "transition-colors duration-base focus:outline-none",
          "focus-visible:ring-2 focus-visible:ring-brand-500 rounded",
        )}
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((opts: Omit<Toast, "id">) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => {
      // Max 3 visible — remove oldest if needed
      const next = [...prev, { ...opts, id }];
      return next.length > 3 ? next.slice(next.length - 3) : next;
    });
  }, []);

  return (
    <ToastContext.Provider value={{ toast, dismiss }}>
      {children}
      {/* Toast container — bottom-right, 24px from edge */}
      <div
        aria-live="polite"
        aria-label="Notifications"
        className="fixed bottom-6 right-6 z-toast flex flex-col gap-2 items-end"
        style={{ zIndex: 1200 }}
      >
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx;
}
