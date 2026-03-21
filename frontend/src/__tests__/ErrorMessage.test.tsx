import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ErrorMessage } from "@/components/ui/ErrorMessage";

describe("ErrorMessage", () => {
  it("renders message text", () => {
    render(<ErrorMessage message="Something went wrong." />);
    expect(screen.getByText("Something went wrong.")).toBeInTheDocument();
  });

  it("renders default title when not provided", () => {
    render(<ErrorMessage message="Error" />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders custom title when provided", () => {
    render(<ErrorMessage title="Load failed" message="Try again." />);
    expect(screen.getByText("Load failed")).toBeInTheDocument();
  });

  it("does not render retry button when onRetry is not provided", () => {
    render(<ErrorMessage message="Error" />);
    expect(screen.queryByText("Retry")).not.toBeInTheDocument();
  });

  it("renders retry button when onRetry is provided", () => {
    render(<ErrorMessage message="Error" onRetry={() => {}} />);
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("calls onRetry when retry button is clicked", () => {
    const onRetry = vi.fn();
    render(<ErrorMessage message="Error" onRetry={onRetry} />);
    fireEvent.click(screen.getByText("Retry"));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
