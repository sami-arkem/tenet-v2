import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Badge } from "@/components/ui/Badge";

describe("Badge", () => {
  it("renders auto-label from badgeLabels map", () => {
    render(<Badge variant="pass" />);
    expect(screen.getByText("PASS")).toBeInTheDocument();
  });

  it("renders custom label override", () => {
    render(<Badge variant="pass" label="Passed" />);
    expect(screen.getByText("Passed")).toBeInTheDocument();
  });

  it("renders unknown variant with uppercased variant string", () => {
    render(<Badge variant="some_status" />);
    expect(screen.getByText("SOME STATUS")).toBeInTheDocument();
  });

  it("applies success styles for pass variant", () => {
    render(<Badge variant="pass" />);
    const el = screen.getByText("PASS");
    expect(el.className).toContain("success");
  });

  it("applies danger styles for fail variant", () => {
    render(<Badge variant="fail" />);
    const el = screen.getByText("FAIL");
    expect(el.className).toContain("danger");
  });

  it("applies warning styles for medium severity", () => {
    render(<Badge variant="medium" />);
    const el = screen.getByText("MEDIUM");
    expect(el.className).toContain("warning");
  });

  it("applies danger styles for critical severity", () => {
    render(<Badge variant="critical" />);
    const el = screen.getByText("CRITICAL");
    expect(el.className).toContain("danger");
  });

  it("renders in_progress status badge", () => {
    render(<Badge variant="in_progress" />);
    expect(screen.getByText("IN PROGRESS")).toBeInTheDocument();
  });

  it("renders open status with neutral styles", () => {
    render(<Badge variant="open" />);
    const el = screen.getByText("OPEN");
    expect(el.className).toContain("neutral");
  });

  it("renders completed with success styles", () => {
    render(<Badge variant="completed" />);
    const el = screen.getByText("COMPLETED");
    expect(el.className).toContain("success");
  });

  it("accepts additional className", () => {
    render(<Badge variant="open" className="extra-class" />);
    const el = screen.getByText("OPEN");
    expect(el.className).toContain("extra-class");
  });

  it("normalises variant to lowercase before lookup", () => {
    render(<Badge variant="PASS" />);
    expect(screen.getByText("PASS")).toBeInTheDocument();
    const el = screen.getByText("PASS");
    expect(el.className).toContain("success");
  });
});
