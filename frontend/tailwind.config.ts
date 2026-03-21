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
        mono: ['"JetBrains Mono"', '"Geist Mono"', "Menlo", "Monaco", "Consolas", "monospace"],
      },
      // ── Bible §1.2 complete design token palette ─────────────────────────
      colors: {
        // Bible §17.2 — Slate-based neutral scale (cool, professional)
        neutral: {
          "0":   "#FFFFFF",
          "50":  "#F8FAFC",
          "100": "#F1F5F9",
          "200": "#E2E8F0",
          "300": "#CBD5E1",
          "400": "#94A3B8",
          "500": "#64748B",
          "600": "#475569",
          "700": "#334155",
          "800": "#1E293B",
          "900": "#0F172A",
          "950": "#020617",
        },
        // Bible §17.2 — Blue primary palette
        brand: {
          "50":  "#EFF6FF",
          "100": "#DBEAFE",
          "200": "#BFDBFE",
          "300": "#93C5FD",
          "400": "#60A5FA",
          "500": "#3B82F6",
          "600": "#2563EB",
          "700": "#1D4ED8",
          "800": "#1E40AF",
          "900": "#1E3A8A",
          "950": "#172554",
        },
        // Bible §17.2 — Semantic colors
        success: { light: "#F0FDF4", base: "#16A34A", dark: "#14532D" },
        warning: { light: "#FFFBEB", base: "#D97706", dark: "#78350F" },
        danger:  { light: "#FEF2F2", base: "#DC2626", dark: "#7F1D1D" },
        info:    { light: "#EFF6FF", base: "#2563EB", dark: "#1E3A8A" },
        // Accent — Sky 500
        accent:  { light: "#F0F9FF", base: "#0EA5E9", dark: "#0C4A6E" },
        // Surface/text convenience tokens
        surface: {
          DEFAULT:         "#FFFFFF",
          subtle:          "#F8FAFC",
          muted:           "#F1F5F9",
          border:          "#E2E8F0",
          "border-strong": "#CBD5E1",
        },
        text: {
          DEFAULT:   "#0F172A",
          secondary: "#475569",
          muted:     "#64748B",
          disabled:  "#CBD5E1",
        },
      },
      // Bible §1.2 font sizes
      fontSize: {
        "10": ["10px", { lineHeight: "1.5" }],
        "11": ["11px", { lineHeight: "1.5" }],
        "12": ["12px", { lineHeight: "1.5" }],
        "13": ["13px", { lineHeight: "1.5" }],
        "14": ["14px", { lineHeight: "1.5" }],
        "15": ["15px", { lineHeight: "1.5" }],
        "16": ["16px", { lineHeight: "1.375" }],
        "18": ["18px", { lineHeight: "1.375" }],
        "20": ["20px", { lineHeight: "1.25" }],
        "22": ["22px", { lineHeight: "1.25" }],
        "24": ["24px", { lineHeight: "1.25" }],
        "28": ["28px", { lineHeight: "1.25" }],
      },
      // Bible §1.2 border radius — max 12px (lg), never larger
      borderRadius: {
        none:    "0",
        sm:      "4px",
        base:    "6px",
        DEFAULT: "6px",
        md:      "8px",
        lg:      "12px",
        xl:      "16px",
        "2xl":   "24px",
        full:    "9999px",
      },
      // Bible: no drop shadows on cards. Only subtle ring.
      boxShadow: {
        none:    "none",
        sm:      "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        base:    "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
        md:      "0 4px 6px -1px rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.07)",
        inner:   "inset 0 2px 4px 0 rgb(0 0 0 / 0.05)",
        ring:    "0 0 0 1px #E2E8F0",
        DEFAULT: "0 0 0 1px #E2E8F0",
      },
      // Bible: no animation > 250ms
      transitionDuration: {
        fast:    "100",
        base:    "150",
        slow:    "250",
        slower:  "500",
        DEFAULT: "150",
      },
      maxWidth: {
        content: "1200px",
        wide:    "1440px",
      },
    },
  },
  plugins: [],
};

export default config;
