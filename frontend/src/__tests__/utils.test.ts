import { describe, it, expect } from "vitest";
import { formatBytes, truncate, isOverdue, isDueSoon } from "@/lib/utils";

describe("formatBytes", () => {
  it("formats 0 bytes", () => expect(formatBytes(0)).toBe("0 B"));
  it("formats kilobytes", () => expect(formatBytes(1024)).toBe("1 KB"));
  it("formats megabytes", () => expect(formatBytes(1_048_576)).toBe("1 MB"));
  it("formats gigabytes", () => expect(formatBytes(1_073_741_824)).toBe("1 GB"));
  it("formats fractional", () => expect(formatBytes(1500)).toBe("1.5 KB"));
});

describe("truncate", () => {
  it("passes through short strings", () => {
    expect(truncate("hello", 10)).toBe("hello");
  });
  it("truncates long strings", () => {
    const long = "a".repeat(100);
    const result = truncate(long, 20);
    expect(result.length).toBe(20);
    expect(result.endsWith("…")).toBe(true);
  });
});

describe("isOverdue", () => {
  it("is overdue when due date < today", () => {
    expect(isOverdue("2025-01-01", "2026-03-20")).toBe(true);
  });
  it("is not overdue when due date >= today", () => {
    expect(isOverdue("2026-04-01", "2026-03-20")).toBe(false);
  });
});

describe("isDueSoon", () => {
  it("is due soon within window", () => {
    expect(isDueSoon("2026-03-25", "2026-03-20", 7)).toBe(true);
  });
  it("is not due soon outside window", () => {
    expect(isDueSoon("2026-04-30", "2026-03-20", 7)).toBe(false);
  });
  it("is not due soon if overdue", () => {
    expect(isDueSoon("2026-03-01", "2026-03-20", 7)).toBe(false);
  });
});
