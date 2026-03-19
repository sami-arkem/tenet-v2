import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Menlo", "Monaco", "Consolas", "monospace"],
      },
      colors: {
        // Tenet design token surface colors — near-monochromatic
        surface: {
          DEFAULT: "#ffffff",
          subtle: "#f8f8f8",
          muted: "#f2f2f2",
          border: "#e4e4e7",
          "border-strong": "#d1d1d6",
        },
        text: {
          DEFAULT: "#18181b",
          secondary: "#52525b",
          muted: "#a1a1aa",
          disabled: "#d4d4d8",
        },
        // Status tokens — used only for real status communication
        status: {
          ready: { bg: "#f0fdf4", text: "#166534", border: "#bbf7d0" },
          blocked: { bg: "#fef2f2", text: "#991b1b", border: "#fecaca" },
          processing: { bg: "#eff6ff", text: "#1d4ed8", border: "#bfdbfe" },
          queued: { bg: "#fffbeb", text: "#92400e", border: "#fde68a" },
          missing: { bg: "#f9fafb", text: "#374151", border: "#e5e7eb" },
          review: { bg: "#fff7ed", text: "#9a3412", border: "#fed7aa" },
          failed: { bg: "#fef2f2", text: "#991b1b", border: "#fecaca" },
          cancelled: { bg: "#f9fafb", text: "#6b7280", border: "#e5e7eb" },
        },
      },
      borderRadius: {
        DEFAULT: "6px",
        sm: "4px",
        md: "8px",
        lg: "10px",
        xl: "12px",
      },
      boxShadow: {
        // Bible: no drop shadows on cards — only use subtle ring
        sm: "0 0 0 1px #e4e4e7",
        DEFAULT: "0 0 0 1px #e4e4e7",
      },
      maxWidth: {
        content: "960px",
        wide: "1200px",
      },
      transitionDuration: {
        DEFAULT: "150ms",
        fast: "100ms",
        normal: "200ms",
        // Bible: no animation longer than 250ms
        slow: "250ms",
      },
    },
  },
  plugins: [],
};

export default config;
