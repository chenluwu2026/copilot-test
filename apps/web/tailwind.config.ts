import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        aims: {
          bg: "#0f1419",
          card: "#1a2332",
          border: "#2d3a4f",
          accent: "#3b82f6",
          research: "#60a5fa",
          trade: "#f97316",
          positive: "#22c55e",
          negative: "#ef4444",
        },
      },
    },
  },
  plugins: [],
};
export default config;
