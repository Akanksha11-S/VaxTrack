/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Public Sans Variable"', "system-ui", "Segoe UI", "sans-serif"],
        serif: ['"Source Serif 4 Variable"', "Georgia", "serif"],
      },
      colors: {
        ink: { DEFAULT: "#14312F", soft: "#3F5A57", muted: "#5B726F" },
        paper: "#F6F9F8",
        line: { DEFAULT: "#DCE6E3", strong: "#C3D3CF" },
        teal: { 50: "#E7F4F1", 100: "#CDE9E4", 200: "#A5D6CE", 600: "#0E7C73", 700: "#0B635C", 800: "#094E49" },
        azure: { 50: "#EAF1F8", 100: "#D3E3F2", 600: "#2A62A0", 700: "#1F4E82" },
        sage: { 50: "#E6F3EA", 100: "#D3EADB", 500: "#4C9A6A", 700: "#2C6B45" },
        amber: { 50: "#FBF1D8", 100: "#F6E2B0", 500: "#D9A21B", 700: "#7C5200" },
        rose: { 50: "#FBE6E3", 100: "#F5CBC5", 500: "#D2584B", 700: "#A12A1F" },
      },
      borderRadius: { panel: "14px", control: "8px" },
      boxShadow: {
        panel: "0 1px 2px rgba(20, 49, 47, 0.06), 0 1px 1px rgba(20, 49, 47, 0.04)",
        lift: "0 8px 24px rgba(20, 49, 47, 0.12)",
      },
    },
  },
  plugins: [],
};
