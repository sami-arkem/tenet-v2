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
        // Neutral scale
        neutral: {
          "0":   "#FFFFFF",
          "50":  "#FAFAFA",
          "100": "#F5F5F4",
          "200": "#E7E5E4",
          "300": "#D6D3D1",
          "400": "#A8A29E",
          "500": "#78716C",
          "600": "#57534E",
          "700": "#44403C",
          "800": "#292524",
          "900": "#1C1917",
          "950": "#0C0A09",
        },
        // Brand (indigo-blue)
        brand: {
          "50":  "#F0F4FF",
          "100": "#E0E9FF",
          "200": "#C7D7FE",
          "300": "#A4BCFD",
          "400": "#7C9CFB",
          "500": "#5574F7",
          "600": "#3D55E8",
          "700": "#3141D1",
          "800": "#2B37AA",
          "900": "#293486",
          "950": "#1C2157",
        },
        // Semantic
        success: { light: "#F0FDF4", base: "#16A34A", dark: "#14532D" },
        warning: { light: "#FFFBEB", base: "#D97706", dark: "#78350F" },
        danger:  { light: "#FEF2F2", base: "#DC2626", dark: "#7F1D1D" },
        info:    { light: "#EFF6FF", base: "#2563EB", dark: "#1E3A8A" },
        // Legacy surface/text tokens — kept so existing components don't break
        surface: {
          DEFAULT:         "#FFFFFF",
          subtle:          "#FAFAFA",
          muted:           "#F5F5F4",
          border:          "#E7E5E4",
          "border-strong": "#D6D3D1",
        },
        text: {
          DEFAULT:   "#292524",
          secondary: "#57534E",
          muted:     "#A8A29E",
          disabled:  "#D6D3D1",
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
        ring:    "0 0 0 1px #E7E5E4",
        DEFAULT: "0 0 0 1px #E7E5E4",
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
