// components/ui/DataTable.tsx — Bible §1.4.4 — TanStack Table v8
"use client";

import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  useReactTable,
  SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Legacy column API (kept for backward compat with existing pages) ──────────
export interface Column<T> {
  key: string;
  header: string;
  width?: string;
  render?: (row: T) => React.ReactNode;
}

interface LegacyDataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  getKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  selectedKey?: string;
  emptyState?: React.ReactNode;
}

export function DataTable<T>({
  columns,
  rows,
  getKey,
  onRowClick,
  selectedKey,
  emptyState,
}: LegacyDataTableProps<T>) {
  if (rows.length === 0) {
    return (
      <div className="py-16 text-center text-14 text-neutral-400">
        {emptyState ?? "No items to display"}
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-neutral-50 border-b border-neutral-200">
            {columns.map((col) => (
              <th
                key={col.key}
                style={col.width ? { width: col.width } : undefined}
                className="px-4 py-3 text-left text-11 font-medium text-neutral-500 uppercase tracking-wider whitespace-nowrap"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-100 bg-white">
          {rows.map((row) => {
            const key = getKey(row);
            const isSelected = key === selectedKey;
            return (
              <tr
                key={key}
                onClick={() => onRowClick?.(row)}
                className={cn(
                  "h-[52px] transition-colors duration-base",
                  onRowClick && "cursor-pointer",
                  isSelected
                    ? "bg-brand-50 border-l-2 border-l-brand-500"
                    : "hover:bg-neutral-50",
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className="px-4 py-0 text-14 text-neutral-700 whitespace-nowrap"
                  >
                    {col.render
                      ? col.render(row)
                      : String((row as Record<string, unknown>)[col.key] ?? "")}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── TanStack-powered table (new, used for findings/remediation) ───────────────
interface TanstackTableProps<TData> {
  columns: ColumnDef<TData>[];
  data: TData[];
  onRowClick?: (row: TData) => void;
  selectedRowId?: string;
  getRowId?: (row: TData) => string;
  loading?: boolean;
  emptyState?: React.ReactNode;
  rowDensity?: "compact" | "default" | "relaxed";
  pageSize?: number;
}

const rowHeights = {
  compact:  "h-11",
  default:  "h-[52px]",
  relaxed:  "h-[60px]",
};

export function TanstackTable<TData>({
  columns,
  data,
  onRowClick,
  selectedRowId,
  getRowId,
  loading = false,
  emptyState,
  rowDensity = "default",
  pageSize = 50,
}: TanstackTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    getRowId,
    state: { sorting },
    initialState: { pagination: { pageSize } },
  });

  if (loading) {
    return <TanstackTableSkeleton rows={5} columns={columns.length} density={rowDensity} />;
  }

  return (
    <div className="w-full">
      <div className="rounded-base border border-neutral-200 overflow-hidden">
        <table className="w-full">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr
                key={headerGroup.id}
                className="bg-neutral-50 border-b border-neutral-200"
              >
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className={cn(
                      "px-4 py-3 text-left",
                      "text-11 font-medium text-neutral-500 uppercase tracking-wider whitespace-nowrap",
                      header.column.getCanSort() &&
                        "cursor-pointer select-none hover:text-neutral-700",
                    )}
                    onClick={header.column.getToggleSortingHandler()}
                    aria-sort={
                      header.column.getIsSorted() === "asc"
                        ? "ascending"
                        : header.column.getIsSorted() === "desc"
                          ? "descending"
                          : "none"
                    }
                  >
                    <div className="flex items-center gap-1.5">
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                      {header.column.getCanSort() && (
                        <span className="text-neutral-300">
                          {header.column.getIsSorted() === "asc" ? (
                            <ChevronUp className="h-3.5 w-3.5 text-neutral-600" />
                          ) : header.column.getIsSorted() === "desc" ? (
                            <ChevronDown className="h-3.5 w-3.5 text-neutral-600" />
                          ) : (
                            <ChevronsUpDown className="h-3.5 w-3.5" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-neutral-100 bg-white">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="py-16 text-center">
                  {emptyState ?? (
                    <p className="text-14 text-neutral-400">No items to display</p>
                  )}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => {
                const rowId = getRowId ? getRowId(row.original) : row.id;
                const isSelected = rowId === selectedRowId;

                return (
                  <tr
                    key={row.id}
                    onClick={() => onRowClick?.(row.original)}
                    className={cn(
                      rowHeights[rowDensity],
                      "transition-colors duration-base",
                      onRowClick && "cursor-pointer",
                      isSelected
                        ? "bg-brand-50 border-l-2 border-l-brand-500"
                        : "hover:bg-neutral-50",
                    )}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td
                        key={cell.id}
                        className="px-4 py-0 text-14 text-neutral-700 whitespace-nowrap"
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {table.getPageCount() > 1 && (
        <div className="flex items-center justify-between px-2 py-3 border-t border-neutral-200">
          <p className="text-13 text-neutral-500">
            Showing{" "}
            {table.getState().pagination.pageIndex *
              table.getState().pagination.pageSize +
              1}
            –
            {Math.min(
              (table.getState().pagination.pageIndex + 1) *
                table.getState().pagination.pageSize,
              data.length,
            )}{" "}
            of {data.length}
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              className={cn(
                "flex items-center justify-center h-7 w-7 rounded-base",
                "text-neutral-500 hover:bg-neutral-100 disabled:opacity-40",
                "transition-colors duration-base",
              )}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              className={cn(
                "flex items-center justify-center h-7 w-7 rounded-base",
                "text-neutral-500 hover:bg-neutral-100 disabled:opacity-40",
                "transition-colors duration-base",
              )}
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function TanstackTableSkeleton({
  rows,
  columns,
  density,
}: {
  rows: number;
  columns: number;
  density: "compact" | "default" | "relaxed";
}) {
  return (
    <div className="w-full rounded-base border border-neutral-200 overflow-hidden animate-pulse">
      <div className="bg-neutral-50 border-b border-neutral-200 h-10" />
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "flex items-center gap-4 px-4 border-b border-neutral-100",
            rowHeights[density],
          )}
        >
          {Array.from({ length: columns }).map((_, j) => (
            <div
              key={j}
              className="h-4 bg-neutral-100 rounded flex-1"
            />
          ))}
        </div>
      ))}
    </div>
  );
}
