import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Input } from "@/components/ui/Input";

describe("Input", () => {
  it("renders without label", () => {
    render(<Input placeholder="Enter value" />);
    expect(screen.getByPlaceholderText("Enter value")).toBeInTheDocument();
  });

  it("renders label and associates it with input", () => {
    render(<Input label="Email address" />);
    const label = screen.getByText("Email address");
    const input = screen.getByRole("textbox");
    expect(label).toBeInTheDocument();
    expect(label.closest("label")).toHaveAttribute("for", input.id);
  });

  it("shows required asterisk when required prop is set", () => {
    render(<Input label="Name" required />);
    // The asterisk is aria-hidden but present in DOM
    expect(screen.getByText("*")).toBeInTheDocument();
  });

  it("sets aria-required when required", () => {
    render(<Input required />);
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-required", "true");
  });

  it("shows error message", () => {
    render(<Input error="This field is required" />);
    expect(screen.getByText("This field is required")).toBeInTheDocument();
  });

  it("sets aria-invalid when error is present", () => {
    render(<Input error="Bad input" />);
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "true");
  });

  it("sets aria-describedby to error element id", () => {
    render(<Input error="Error msg" />);
    const input = screen.getByRole("textbox");
    const errorId = input.getAttribute("aria-describedby");
    expect(errorId).toBeTruthy();
    const errorEl = document.getElementById(errorId!);
    expect(errorEl?.textContent).toBe("Error msg");
  });

  it("shows helpText when no error", () => {
    render(<Input helpText="We'll never share your email." />);
    expect(screen.getByText("We'll never share your email.")).toBeInTheDocument();
  });

  it("hides helpText when error is present", () => {
    render(<Input error="Error" helpText="Helper text" />);
    expect(screen.queryByText("Helper text")).not.toBeInTheDocument();
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("fires onChange handler", () => {
    const handler = vi.fn();
    render(<Input onChange={handler} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "hello" } });
    expect(handler).toHaveBeenCalledOnce();
  });

  it("is disabled when disabled prop is set", () => {
    render(<Input disabled />);
    expect(screen.getByRole("textbox")).toBeDisabled();
  });

  it("renders prefix slot", () => {
    render(<Input prefix={<span data-testid="pfx">$</span>} />);
    expect(screen.getByTestId("pfx")).toBeInTheDocument();
  });

  it("renders suffix slot", () => {
    render(<Input suffix={<span data-testid="sfx">kg</span>} />);
    expect(screen.getByTestId("sfx")).toBeInTheDocument();
  });

  it("uses aria-invalid=false when no error", () => {
    render(<Input />);
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "false");
  });
});
