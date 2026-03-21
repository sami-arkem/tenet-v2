import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatDateOnly(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function isOverdue(dueDateIso: string, today: string): boolean {
  return dueDateIso < today;
}

export function isDueSoon(
  dueDateIso: string,
  today: string,
  windowDays = 7,
): boolean {
  const dueMs = new Date(dueDateIso).getTime();
  const todayMs = new Date(today).getTime();
  const windowMs = windowDays * 24 * 60 * 60 * 1000;
  return dueMs >= todayMs && dueMs <= todayMs + windowMs;
}

export function truncate(str: string, max = 80): string {
  return str.length > max ? str.slice(0, max - 1) + "…" : str;
}
