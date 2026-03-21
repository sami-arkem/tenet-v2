// components/ui/Button.tsx — Bible §1.4.1
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";
import { ButtonHTMLAttributes, forwardRef, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "link";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
  fullWidth?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-700 text-white hover:bg-brand-800 focus-visible:ring-brand-300 border border-transparent shadow-sm",
  secondary:
    "bg-white border border-neutral-200 text-neutral-700 hover:bg-neutral-50 focus-visible:ring-brand-300",
  ghost:
    "bg-transparent text-neutral-700 hover:bg-neutral-100 border border-transparent focus-visible:ring-brand-300",
  danger:
    "bg-danger-light border border-danger-base text-danger-dark hover:bg-danger-base hover:text-white focus-visible:ring-danger-base",
  link: "bg-transparent text-brand-500 hover:underline p-0 h-auto border-none focus-visible:ring-brand-300",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-7 px-2 text-13 gap-1.5",
  md: "h-8 px-3 text-14 gap-2",
  lg: "h-9 px-4 text-15 gap-2",
};

const iconSizeClasses: Record<ButtonSize, string> = {
  sm: "h-3.5 w-3.5",
  md: "h-4 w-4",
  lg: "h-4 w-4",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "primary",
      size = "md",
      loading = false,
      iconLeft,
      iconRight,
      fullWidth = false,
      disabled,
      children,
      className,
      ...props
    },
    ref,
  ) {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        aria-busy={loading}
        className={cn(
          "inline-flex items-center justify-center font-medium rounded-base",
          "transition-colors duration-base",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
          "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
          "whitespace-nowrap select-none",
          variant !== "link" && sizeClasses[size],
          variantClasses[variant],
          fullWidth && "w-full",
          className,
        )}
        {...props}
      >
        {loading ? (
          <Loader2
            className={cn("animate-spin", iconSizeClasses[size])}
            aria-hidden="true"
          />
        ) : (
          <>
            {iconLeft && (
              <span
                className={cn("shrink-0", iconSizeClasses[size])}
                aria-hidden="true"
              >
                {iconLeft}
              </span>
            )}
            {children}
            {iconRight && (
              <span
                className={cn("shrink-0", iconSizeClasses[size])}
                aria-hidden="true"
              >
                {iconRight}
              </span>
            )}
          </>
        )}
      </button>
    );
  },
);

Button.displayName = "Button";
