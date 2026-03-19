import { cn } from "@/lib/utils";

export interface Column<T> {
  key: string;
  header: string;
  width?: string;
  className?: string;
  render: (row: T, index: number) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  getKey: (row: T, index: number) => string;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  getKey,
  onRowClick,
  emptyMessage = "No records found.",
  className,
}: DataTableProps<T>) {
  return (
    <div
      className={cn(
        "border border-surface-border rounded overflow-hidden",
        className,
      )}
    >
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-surface-subtle border-b border-surface-border">
            {columns.map((col) => (
              <th
                key={col.key}
                style={col.width ? { width: col.width } : undefined}
                className={cn(
                  "px-4 py-2.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wide whitespace-nowrap",
                  col.className,
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-surface divide-y divide-surface-border">
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-text-muted text-sm"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr
                key={getKey(row, i)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(
                  onRowClick &&
                    "cursor-pointer hover:bg-surface-subtle transition-fast",
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn(
                      "px-4 py-3 text-sm",
                      col.className,
                    )}
                  >
                    {col.render(row, i)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
