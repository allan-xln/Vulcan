import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "../../shared/domain/src/**/*.{ts,tsx}",
    "./node_modules/@tremor/react/dist/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#f7f3ea",
        ink: "#14213d",
        signal: "#fca311",
        accent: "#2a9d8f",
        tremor: {
          brand: {
            faint: "#fff7ed",
            muted: "#fed7aa",
            subtle: "#fb923c",
            DEFAULT: "#f97316",
            emphasis: "#ea580c",
            inverted: "#0a0a0a"
          },
          background: {
            muted: "#18181b",
            subtle: "#27272a",
            DEFAULT: "#09090b",
            emphasis: "#3f3f46"
          },
          border: "#27272a",
          ring: "#fb923c",
          content: {
            subtle: "#71717a",
            DEFAULT: "#a1a1aa",
            emphasis: "#e4e4e7",
            strong: "#fafafa",
            inverted: "#0a0a0a"
          }
        },
        "dark-tremor": {
          brand: {
            faint: "#431407",
            muted: "#7c2d12",
            subtle: "#fb923c",
            DEFAULT: "#f97316",
            emphasis: "#fdba74",
            inverted: "#0a0a0a"
          },
          background: {
            muted: "#111113",
            subtle: "#18181b",
            DEFAULT: "#09090b",
            emphasis: "#27272a"
          },
          border: "#27272a",
          ring: "#fb923c",
          content: {
            subtle: "#71717a",
            DEFAULT: "#a1a1aa",
            emphasis: "#e4e4e7",
            strong: "#fafafa",
            inverted: "#0a0a0a"
          }
        }
      },
      boxShadow: {
        "tremor-input": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        "tremor-card": "0 18px 70px rgba(0,0,0,0.28)",
        "tremor-dropdown": "0 18px 45px rgba(0,0,0,0.35)",
        "dark-tremor-input": "0 1px 2px 0 rgb(0 0 0 / 0.35)",
        "dark-tremor-card": "0 18px 70px rgba(0,0,0,0.36)",
        "dark-tremor-dropdown": "0 18px 45px rgba(0,0,0,0.45)"
      },
      borderRadius: {
        "tremor-small": "0.375rem",
        "tremor-default": "0.5rem",
        "tremor-full": "9999px"
      },
      fontSize: {
        "tremor-label": ["0.75rem", { lineHeight: "1rem" }],
        "tremor-default": ["0.875rem", { lineHeight: "1.25rem" }],
        "tremor-title": ["1.125rem", { lineHeight: "1.75rem" }],
        "tremor-metric": ["1.875rem", { lineHeight: "2.25rem" }]
      }
    }
  },
  plugins: []
};

export default config;
