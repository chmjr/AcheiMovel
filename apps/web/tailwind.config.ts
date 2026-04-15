import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18211f",
        moss: "#45624e",
        clay: "#b85c38",
        paper: "#f7f8f4"
      }
    }
  },
  plugins: []
};

export default config;
