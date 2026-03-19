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
        "bg-white border border-neutral-200 rounded-base",
        padding && "p-6",
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
      className={cn(bordered && "border-t border-neutral-200 pt-4 mt-4", className)}
    >
      {children}
    </div>
  );
}
