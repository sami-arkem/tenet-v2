import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusBadge } from "@/components/ui/StatusBadge";

describe("StatusBadge", () => {
  it("renders READY with green styling", () => {
    render(<StatusBadge status="READY" />);
    const badge = screen.getByText("READY");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("emerald");
  });

  it("renders BLOCKED with red styling", () => {
    render(<StatusBadge status="BLOCKED" />);
    const badge = screen.getByText("BLOCKED");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("red");
  });

  it("renders PROCESSING with blue styling", () => {
    render(<StatusBadge status="PROCESSING" />);
    const badge = screen.getByText("PROCESSING");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("blue");
  });

  it("renders custom label", () => {
    render(<StatusBadge status="READY" label="All Clear" />);
    expect(screen.getByText("All Clear")).toBeInTheDocument();
  });

  it("replaces underscores in label with spaces", () => {
    render(<StatusBadge status="OCR_REQUIRED" />);
    expect(screen.getByText("OCR REQUIRED")).toBeInTheDocument();
  });

  it("renders unknown status with fallback styling", () => {
    render(<StatusBadge status="SOME_UNKNOWN_STATE" />);
    expect(screen.getByText("SOME UNKNOWN STATE")).toBeInTheDocument();
  });
});
