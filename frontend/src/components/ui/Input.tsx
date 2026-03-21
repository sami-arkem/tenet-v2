// components/ui/Input.tsx — Bible §1.4.2
"use client";

import { cn } from "@/lib/utils";
import { forwardRef, InputHTMLAttributes, ReactNode, useId } from "react";

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "prefix" | "suffix"> {
  label?: string;
  error?: string;
  helpText?: string;
  prefix?: ReactNode;
  suffix?: ReactNode;
  inputSize?: "sm" | "md" | "lg";
  required?: boolean;
}

const inputSizeClasses = {
  sm: "h-8 text-13 px-2.5",
  md: "h-9 text-14 px-3",
  lg: "h-10 text-15 px-3.5",
};

export const Input = forwardRef<HTMLInputElement, InputProps>(
  function Input(
    {
      label,
      error,
      helpText,
      prefix,
      suffix,
      inputSize = "md",
      required,
      id: idProp,
      className,
      ...props
    },
    ref,
  ) {
    const generatedId = useId();
    const inputId = idProp ?? generatedId;
    const errorId = `${inputId}-error`;
    const helpId = `${inputId}-help`;

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-13 font-medium text-neutral-600"
          >
            {label}
            {required && (
              <span className="ml-1 text-danger-base" aria-hidden="true">
                *
              </span>
            )}
          </label>
        )}
        <div className="relative flex items-center">
          {prefix && (
            <div className="absolute left-3 flex items-center text-neutral-400 pointer-events-none">
              {prefix}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-required={required}
            aria-invalid={!!error}
            aria-describedby={
              [error && errorId, helpText && helpId]
                .filter(Boolean)
                .join(" ") || undefined
            }
            className={cn(
              "w-full rounded-base border bg-white font-sans",
              "placeholder:text-neutral-400 text-neutral-800",
              "transition-colors duration-base",
              "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500",
              "disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-neutral-50",
              inputSizeClasses[inputSize],
              error
                ? "border-danger-base focus:ring-danger-base"
                : "border-neutral-200 hover:border-neutral-300",
              prefix && "pl-9",
              suffix && "pr-9",
              className,
            )}
            {...props}
          />
          {suffix && (
            <div className="absolute right-3 flex items-center text-neutral-400 pointer-events-none">
              {suffix}
            </div>
          )}
        </div>
        {error && (
          <p id={errorId} className="text-12 text-danger-dark" role="alert">
            {error}
          </p>
        )}
        {helpText && !error && (
          <p id={helpId} className="text-12 text-neutral-400">
            {helpText}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
