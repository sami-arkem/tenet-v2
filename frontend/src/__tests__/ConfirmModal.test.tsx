import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ConfirmModal } from "@/components/ui/ConfirmModal";

function renderModal(props: Partial<React.ComponentProps<typeof ConfirmModal>> = {}) {
  const defaults = {
    open: true,
    title: "Confirm action",
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  };
  return render(<ConfirmModal {...defaults} {...props} />);
}

describe("ConfirmModal", () => {
  it("renders nothing when open=false", () => {
    const { container } = renderModal({ open: false });
    expect(container.firstChild).toBeNull();
  });

  it("renders title when open", () => {
    renderModal({ title: "Delete this item?" });
    expect(screen.getByText("Delete this item?")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    renderModal({ description: "This action cannot be undone." });
    expect(screen.getByText("This action cannot be undone.")).toBeInTheDocument();
  });

  it("calls onConfirm when confirm button is clicked", () => {
    const onConfirm = vi.fn();
    renderModal({ onConfirm, confirmLabel: "Delete" });
    fireEvent.click(screen.getByText("Delete"));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("calls onCancel when cancel button is clicked", () => {
    const onCancel = vi.fn();
    renderModal({ onCancel, cancelLabel: "No, keep it" });
    fireEvent.click(screen.getByText("No, keep it"));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("calls onCancel when close button (X) is clicked", () => {
    const onCancel = vi.fn();
    renderModal({ onCancel });
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("calls onCancel when backdrop is clicked", () => {
    const onCancel = vi.fn();
    renderModal({ onCancel });
    const backdrop = document.querySelector('[aria-hidden="true"]') as HTMLElement;
    fireEvent.click(backdrop);
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("calls onCancel on Escape key", () => {
    const onCancel = vi.fn();
    renderModal({ onCancel });
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("has role=dialog", () => {
    renderModal();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("has aria-labelledby pointing to modal title", () => {
    renderModal({ title: "My title" });
    const dialog = screen.getByRole("dialog");
    const titleId = dialog.getAttribute("aria-labelledby");
    expect(titleId).toBeTruthy();
    expect(document.getElementById(titleId!)?.textContent).toBe("My title");
  });

  it("confirm button has danger styles when destructive=true", () => {
    renderModal({ destructive: true, confirmLabel: "Delete" });
    const btn = screen.getByText("Delete");
    expect(btn.className).toContain("danger");
  });

  it("confirm button has brand styles when destructive=false", () => {
    renderModal({ destructive: false, confirmLabel: "OK" });
    const btn = screen.getByText("OK");
    expect(btn.className).toContain("brand");
  });

  it("renders children slot", () => {
    renderModal({ children: <p>Extra content here</p> });
    expect(screen.getByText("Extra content here")).toBeInTheDocument();
  });
});
