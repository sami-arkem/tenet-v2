import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatRow } from "@/components/ui/StatRow";

describe("StatRow", () => {
  it("renders all stat labels and values", () => {
    render(
      <StatRow
        stats={[
          { label: "total", value: 42 },
          { label: "open", value: 7 },
        ]}
      />,
    );
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("total")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("open")).toBeInTheDocument();
  });

  it("renders string values", () => {
    render(<StatRow stats={[{ label: "status", value: "Active" }]} />);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies danger color for error variant", () => {
    render(
      <StatRow stats={[{ label: "blocked", value: 3, variant: "error" }]} />,
    );
    const value = screen.getByText("3");
    expect(value.className).toContain("danger");
  });

  it("applies success color for success variant", () => {
    render(
      <StatRow stats={[{ label: "ready", value: 5, variant: "success" }]} />,
    );
    const value = screen.getByText("5");
    expect(value.className).toContain("success");
  });

  it("applies warning color for warning variant", () => {
    render(
      <StatRow stats={[{ label: "soon", value: 2, variant: "warning" }]} />,
    );
    const value = screen.getByText("2");
    expect(value.className).toContain("warning");
  });

  it("applies muted color for muted variant", () => {
    render(
      <StatRow stats={[{ label: "na", value: 0, variant: "muted" }]} />,
    );
    const value = screen.getByText("0");
    expect(value.className).toContain("neutral-400");
  });

  it("uses default neutral color for default variant", () => {
    render(<StatRow stats={[{ label: "items", value: 10, variant: "default" }]} />);
    const value = screen.getByText("10");
    expect(value.className).toContain("neutral-800");
  });

  it("renders multiple stats side by side", () => {
    render(
      <StatRow
        stats={[
          { label: "a", value: 1 },
          { label: "b", value: 2 },
          { label: "c", value: 3 },
        ]}
      />,
    );
    expect(screen.getAllByText(/^[123]$/).length).toBe(3);
  });
});
