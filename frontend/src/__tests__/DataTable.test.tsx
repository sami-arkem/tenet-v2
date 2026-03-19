import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DataTable, Column } from "@/components/ui/DataTable";

interface Row {
  id: string;
  name: string;
  status: string;
}

const COLUMNS: Column<Row>[] = [
  { key: "name", header: "Name", render: (r) => r.name },
  { key: "status", header: "Status", render: (r) => r.status },
];

const ROWS: Row[] = [
  { id: "1", name: "Alpha", status: "READY" },
  { id: "2", name: "Beta", status: "BLOCKED" },
];

describe("DataTable", () => {
  it("renders headers", () => {
    render(
      <DataTable columns={COLUMNS} rows={ROWS} getKey={(r) => r.id} />,
    );
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("renders row data", () => {
    render(
      <DataTable columns={COLUMNS} rows={ROWS} getKey={(r) => r.id} />,
    );
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
  });

  it("shows empty message when no rows", () => {
    render(
      <DataTable
        columns={COLUMNS}
        rows={[]}
        getKey={(r) => r.id}
        emptyMessage="Nothing here."
      />,
    );
    expect(screen.getByText("Nothing here.")).toBeInTheDocument();
  });

  it("calls onRowClick when row is clicked", () => {
    const handler = vi.fn();
    render(
      <DataTable
        columns={COLUMNS}
        rows={ROWS}
        getKey={(r) => r.id}
        onRowClick={handler}
      />,
    );
    fireEvent.click(screen.getByText("Alpha"));
    expect(handler).toHaveBeenCalledWith(ROWS[0]);
  });
});
