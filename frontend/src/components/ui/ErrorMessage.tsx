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
      <AlertTriangle size={20} className="text-danger-base mb-3" />
      <p className="text-14 font-medium text-neutral-600">{title}</p>
      <p className="mt-1 text-13 text-neutral-400 max-w-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 flex items-center gap-1.5 text-13 text-neutral-500 hover:text-neutral-800 transition-colors duration-base"
        >
          <RefreshCw size={12} />
          Retry
        </button>
      )}
    </div>
  );
}
