import { cn } from "@/lib/utils";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
}

export function Card({ children, className, padding = true }: CardProps) {
  return (
    <div
      className={cn(
        "bg-surface border border-surface-border rounded",
        padding && "p-5",
        className,
      )}
    >
      {children}
    </div>
  );
}

interface CardSectionProps {
  children: React.ReactNode;
  className?: string;
  bordered?: boolean;
}

export function CardSection({
  children,
  className,
  bordered = false,
}: CardSectionProps) {
  return (
    <div
      className={cn(bordered && "border-t border-surface-border pt-4 mt-4", className)}
    >
      {children}
    </div>
  );
}
