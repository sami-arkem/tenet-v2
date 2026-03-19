import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({
  title = "Something went wrong",
  message,
  onRetry,
}: ErrorMessageProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <AlertTriangle size={20} className="text-red-500 mb-3" />
      <p className="text-sm font-medium text-text-secondary">{title}</p>
      <p className="mt-1 text-xs text-text-muted max-w-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 flex items-center gap-1.5 text-xs text-text-secondary hover:text-text transition-fast"
        >
          <RefreshCw size={12} />
          Retry
        </button>
      )}
    </div>
  );
}
