/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          base:     "#ffffff",
          surface:  "#ffffff",
          elevated: "#f9fafb",
          border:   "#e5e7eb",
        },
        brand: {
          DEFAULT: "#FF6B2C",
          light:   "#FF8A57",
          dim:     "#FFF0EA",
          deep:    "#e55a1f",
        },
        accent: {
          teal:   "#00BCD4",
          green:  "#10B981",
          purple: "#8B5CF6",
          gold:   "#FFB800",
          red:    "#EF4444",
          blue:   "#3B82F6",
          amber:  "#F59E0B",
          pink:   "#EC4899",
          cyan:   "#06b6d4",
        },
        text: {
          primary:   "#111827",
          secondary: "#374151",
          muted:     "#9CA3AF",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};
