import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PageHeader } from "@/components/ui/PageHeader";

describe("PageHeader", () => {
  it("renders title", () => {
    render(<PageHeader title="Dashboard" />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("title is an h1 element", () => {
    render(<PageHeader title="Audits" />);
    const h1 = screen.getByText("Audits");
    expect(h1.tagName).toBe("H1");
  });

  it("title has correct Bible typography class (text-28)", () => {
    render(<PageHeader title="Reports" />);
    const h1 = screen.getByText("Reports");
    expect(h1.className).toContain("text-28");
  });

  it("title has font-medium (weight 500 — Bible §1.1)", () => {
    render(<PageHeader title="Findings" />);
    const h1 = screen.getByText("Findings");
    expect(h1.className).toContain("font-medium");
    expect(h1.className).not.toContain("font-semibold");
  });

  it("renders subtitle when provided", () => {
    render(<PageHeader title="Dashboard" subtitle="Posture overview" />);
    expect(screen.getByText("Posture overview")).toBeInTheDocument();
  });

  it("does not render subtitle element when omitted", () => {
    render(<PageHeader title="Dashboard" />);
    expect(screen.queryByText(/posture/i)).not.toBeInTheDocument();
  });

  it("renders action slot", () => {
    render(
      <PageHeader title="Audits" action={<button>New Audit</button>} />,
    );
    expect(screen.getByText("New Audit")).toBeInTheDocument();
  });

  it("renders breadcrumbs when provided", () => {
    render(
      <PageHeader
        title="Details"
        breadcrumbs={[
          { label: "Audits", href: "/audits" },
          { label: "My System", href: "/audits/123" },
          { label: "Findings" },
        ]}
      />,
    );
    expect(screen.getByText("Audits")).toBeInTheDocument();
    expect(screen.getByText("My System")).toBeInTheDocument();
    expect(screen.getAllByText("Findings").length).toBeGreaterThanOrEqual(1);
  });

  it("breadcrumb links have href attribute", () => {
    render(
      <PageHeader
        title="Findings"
        breadcrumbs={[{ label: "Audits", href: "/audits" }, { label: "Findings" }]}
      />,
    );
    const link = screen.getByText("Audits").closest("a");
    expect(link).toHaveAttribute("href", "/audits");
  });

  it("last breadcrumb has no link when no href", () => {
    render(
      <PageHeader
        title="Findings"
        breadcrumbs={[{ label: "Findings" }]}
      />,
    );
    const el = screen.getByText("Findings", { selector: "span" });
    expect(el.tagName).toBe("SPAN");
  });

  it("does not render nav when breadcrumbs is empty array", () => {
    const { container } = render(
      <PageHeader title="Dashboard" breadcrumbs={[]} />,
    );
    expect(container.querySelector("nav")).toBeNull();
  });
});
