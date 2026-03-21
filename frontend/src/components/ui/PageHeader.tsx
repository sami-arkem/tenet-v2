import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
  breadcrumbs?: Array<{ label: string; href?: string }>;
}

export function PageHeader({
  title,
  subtitle,
  action,
  className,
  breadcrumbs,
}: PageHeaderProps) {
  return (
    <div className={cn("mb-8", className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-1.5 mb-3 text-12 text-neutral-400">
          {breadcrumbs.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {i > 0 && <span>/</span>}
              {crumb.href ? (
                <a
                  href={crumb.href}
                  className="hover:text-neutral-600 transition-colors duration-base"
                >
                  {crumb.label}
                </a>
              ) : (
                <span className="text-neutral-600">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-28 font-medium text-neutral-800">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-1 text-14 text-neutral-500">{subtitle}</p>
          )}
        </div>
        {action && <div className="flex-none">{action}</div>}
      </div>
    </div>
  );
}
