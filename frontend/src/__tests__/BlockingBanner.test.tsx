import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { BlockingBanner } from "@/components/ui/BlockingBanner";

describe("BlockingBanner", () => {
  it("renders nothing when reasons is empty", () => {
    const { container } = render(<BlockingBanner reasons={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders a single reason as a paragraph", () => {
    render(<BlockingBanner reasons={["OCR extraction failed"]} />);
    expect(screen.getByText("OCR extraction failed")).toBeInTheDocument();
  });

  it("renders multiple reasons as a list", () => {
    render(
      <BlockingBanner
        reasons={["Missing evidence", "Classification required"]}
      />,
    );
    expect(screen.getByText("Missing evidence")).toBeInTheDocument();
    expect(screen.getByText("Classification required")).toBeInTheDocument();
  });

  it("renders title when provided", () => {
    render(
      <BlockingBanner
        title="Audit is blocked"
        reasons={["Missing AML policy"]}
      />,
    );
    expect(screen.getByText("Audit is blocked")).toBeInTheDocument();
  });

  it("has role=alert for accessibility", () => {
    render(<BlockingBanner reasons={["some reason"]} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("warning variant renders amber styling", () => {
    render(
      <BlockingBanner reasons={["something"]} variant="warning" />,
    );
    const el = screen.getByRole("alert");
    expect(el.className).toContain("amber");
  });
});
