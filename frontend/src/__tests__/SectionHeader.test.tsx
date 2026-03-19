import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SectionHeader } from "@/components/ui/SectionHeader";

describe("SectionHeader", () => {
  it("renders title", () => {
    render(<SectionHeader title="Findings" />);
    expect(screen.getByText("Findings")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    render(<SectionHeader title="Findings" subtitle="Last 30 days" />);
    expect(screen.getByText("Last 30 days")).toBeInTheDocument();
  });

  it("does not render subtitle element when omitted", () => {
    const { container } = render(<SectionHeader title="Findings" />);
    expect(container.querySelector("p")).toBeNull();
  });

  it("renders action slot when provided", () => {
    render(
      <SectionHeader
        title="Findings"
        action={<button>Export</button>}
      />,
    );
    expect(screen.getByText("Export")).toBeInTheDocument();
  });

  it("title is an h2 element", () => {
    render(<SectionHeader title="Section" />);
    const heading = screen.getByText("Section");
    expect(heading.tagName).toBe("H2");
  });

  it("accepts additional className", () => {
    const { container } = render(
      <SectionHeader title="Section" className="mt-8" />,
    );
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("mt-8");
  });
});
