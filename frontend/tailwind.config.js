/** @type {import('tailwindcss').Config} */
// Palette taken from the AC_ON milestone slide deck: dark roast background,
// bronze rules, broadcast gold (YES / Team A) and signal red (NO / Team B).
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#140E09",
          900: "#1B140D",
          800: "#231A12",
          700: "#2C2117",
          600: "#3A2D1E",
          500: "#4B3A26",
        },
        bronze: { DEFAULT: "#6A5530", light: "#8A6A1E" },
        gold: { DEFAULT: "#F5C842", dim: "#D4B03A", deep: "#5C4A16" },
        signal: { DEFAULT: "#E0242F", soft: "#D8303A", deep: "#4A1717" },
        cream: "#EDE3D0",
        paper: "#FBF1DE",
        sand: "#B7A98D",
        dust: "#7F7462",
        win: { DEFAULT: "#8FCB6B", deep: "#1F2E16" },
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
