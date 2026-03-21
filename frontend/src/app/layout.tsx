import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import { ToastProvider } from "@/components/ui/Toast";
import { ConditionalShell } from "./ConditionalShell";

export const metadata: Metadata = {
  title: "Tenet — Compliance Intelligence Platform",
  description: "The operating system for modern compliance. Deterministic, evidence-grounded, enterprise-grade.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <ToastProvider>
            <ConditionalShell>{children}</ConditionalShell>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
