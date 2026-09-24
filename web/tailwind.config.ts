import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    colors: ({ colors }) => ({
      ...colors,
      sky: {
        50: "#f3ecdf",
        100: "#f3ecdf",
        200: "#e7dcc8",
        300: "#e7a15a",
        400: "#d4924a",
        500: "#c4843e",
        600: "#a86d32",
        700: "#8c5828",
        800: "#6e4520",
        900: "#4e3118",
        950: "#2c1c0e",
      },
    }),
    extend: {
      colors: {
        ink: "#141910",
        panel: "#10160f",
        mist: "#b7aa93",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        display: ["var(--font-display)", "ui-serif", "Georgia"],
      },
    },
  },
  plugins: [],
};

export default config;
