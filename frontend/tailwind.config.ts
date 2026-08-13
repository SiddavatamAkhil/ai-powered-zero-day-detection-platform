import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Enterprise dark-theme palette — deep navy base (Defender/Falcon-style),
        // not pure black, so glass panels have somewhere to sit visually.
        base: {
          950: "#05070D",
          900: "#0B1220",
          800: "#111A2E",
          700: "#1B2740",
        },
        accent: {
          blue: "#3B82F6",
          cyan: "#22D3EE",
          purple: "#8B5CF6",
        },
        severity: {
          critical: "#EF4444",
          high: "#F97316",
          medium: "#F59E0B",
          low: "#22C55E",
          info: "#3B82F6",
        },
      },
      backdropBlur: { xs: "2px" },
      boxShadow: {
        glass: "0 8px 32px rgba(0, 0, 0, 0.35)",
        glow: "0 0 24px rgba(59, 130, 246, 0.35)",
      },
      borderRadius: { xl2: "1.25rem" },
    },
  },
  plugins: [],
};

export default config;
