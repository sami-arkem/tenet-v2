import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Card, CardSection } from "@/components/ui/Card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText("Card content")).toBeInTheDocument();
  });

  it("has white background and border classes", () => {
    const { container } = render(<Card>Content</Card>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("bg-white");
    expect(el.className).toContain("border-neutral-200");
  });

  it("applies default padding (p-6)", () => {
    const { container } = render(<Card>Content</Card>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("p-6");
  });

  it("omits padding when padding=false", () => {
    const { container } = render(<Card padding={false}>Content</Card>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).not.toContain("p-6");
  });

  it("accepts additional className", () => {
    const { container } = render(<Card className="mb-4">Content</Card>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("mb-4");
  });
});

describe("CardSection", () => {
  it("renders children", () => {
    render(<CardSection>Section content</CardSection>);
    expect(screen.getByText("Section content")).toBeInTheDocument();
  });

  it("adds border when bordered=true", () => {
    const { container } = render(<CardSection bordered>Content</CardSection>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("border-t");
    expect(el.className).toContain("border-neutral-200");
  });

  it("does not add border when bordered=false (default)", () => {
    const { container } = render(<CardSection>Content</CardSection>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).not.toContain("border-t");
  });
});
