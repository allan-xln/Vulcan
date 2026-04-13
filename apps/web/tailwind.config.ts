import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "../../packages/domain/src/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#f7f3ea",
        ink: "#14213d",
        signal: "#fca311",
        accent: "#2a9d8f"
      }
    }
  },
  plugins: []
};

export default config;

