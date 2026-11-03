/** @type {import('tailwindcss').Config} */
// Modern dark trading palette. Blue is the product/action accent; green and
// rose are reserved for YES/profit and NO/loss semantics where possible.
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#05070C",
          900: "#080B12",
          800: "#0B1220",
          700: "#111827",
          600: "#182235",
          500: "#243248",
        },
        bronze: { DEFAULT: "#334155", light: "#475569" },
        gold: { DEFAULT: "#3B82F6", dim: "#60A5FA", deep: "#172554" },
        signal: { DEFAULT: "#F43F5E", soft: "#FB7185", deep: "#4C0519" },
        cream: "#E2E8F0",
        paper: "#F8FAFC",
        sand: "#94A3B8",
        dust: "#64748B",
        win: { DEFAULT: "#22C55E", deep: "#052E16" },
      },
      fontFamily: {
        display: ['"Chakra Petch"', "system-ui", "sans-serif"],
        sans: ['"Barlow"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
