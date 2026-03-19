import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { EmptyState } from "@/components/ui/EmptyState";

describe("EmptyState", () => {
  it("renders the title", () => {
    render(<EmptyState title="No items found" />);
    expect(screen.getByText("No items found")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(
      <EmptyState
        title="No items"
        description="Create one to get started."
      />,
    );
    expect(
      screen.getByText("Create one to get started."),
    ).toBeInTheDocument();
  });

  it("renders action when provided", () => {
    render(
      <EmptyState
        title="Nothing here"
        action={<button>Create</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Create" })).toBeInTheDocument();
  });
});
