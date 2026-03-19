import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DetailPanel } from "@/components/ui/DetailPanel";

function renderPanel(props: Partial<React.ComponentProps<typeof DetailPanel>> = {}) {
  const defaults = {
    isOpen: true,
    onClose: vi.fn(),
    title: "Panel Title",
    children: <p>Panel content</p>,
  };
  return render(<DetailPanel {...defaults} {...props} />);
}

describe("DetailPanel", () => {
  it("renders children when open", () => {
    renderPanel({ isOpen: true });
    expect(screen.getByText("Panel content")).toBeInTheDocument();
  });

  it("renders title", () => {
    renderPanel({ title: "Finding Detail" });
    expect(screen.getByText("Finding Detail")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    renderPanel({ subtitle: "Control 3.1" });
    expect(screen.getByText("Control 3.1")).toBeInTheDocument();
  });

  it("does not render subtitle when omitted", () => {
    renderPanel({ subtitle: undefined });
    expect(screen.queryByText("Control 3.1")).not.toBeInTheDocument();
  });

  it("has role=complementary", () => {
    renderPanel();
    expect(screen.getByRole("complementary")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    renderPanel({ onClose });
    fireEvent.click(screen.getByRole("button", { name: /close panel/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose when backdrop is clicked", () => {
    const onClose = vi.fn();
    renderPanel({ isOpen: true, onClose });
    // backdrop is the aria-hidden div
    const backdrop = document.querySelector('[aria-hidden="true"]') as HTMLElement;
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose on Escape key", () => {
    const onClose = vi.fn();
    renderPanel({ isOpen: true, onClose });
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does not call onClose on Escape when closed", () => {
    const onClose = vi.fn();
    renderPanel({ isOpen: false, onClose });
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).not.toHaveBeenCalled();
  });

  it("applies translate-x-full when closed", () => {
    renderPanel({ isOpen: false });
    const panel = screen.getByRole("complementary");
    expect(panel.className).toContain("translate-x-full");
  });

  it("applies translate-x-0 when open", () => {
    renderPanel({ isOpen: true });
    const panel = screen.getByRole("complementary");
    expect(panel.className).toContain("translate-x-0");
  });

  it("does not show backdrop when closed", () => {
    renderPanel({ isOpen: false });
    // aria-hidden backdrop div should not be present
    const backdrop = document.querySelector('[aria-hidden="true"]');
    expect(backdrop).toBeNull();
  });
});
