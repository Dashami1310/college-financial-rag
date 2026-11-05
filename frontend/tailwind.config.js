/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Deep "ledger" navy surfaces
        ink: {
          950: "#070B14",
          900: "#0B1120",
          800: "#111A2E",
          700: "#182338",
          600: "#22304A",
          500: "#374863",
        },
        // Financial-health teal/emerald accent
        ledger: {
          300: "#6EE7C8",
          400: "#3DDBB0",
          500: "#17B893",
          600: "#0F9A7C",
          700: "#0B7A63",
        },
        // Risk / anomaly amber-rose scale
        risk: {
          low: "#3DDBB0",
          mid: "#F4B740",
          high: "#F0654C",
          critical: "#E23B5D",
        },
        parchment: "#EAE6DC",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "system-ui", "sans-serif"],
        body: ["'Inter'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 20px 40px -20px rgba(0,0,0,0.6)",
        glow: "0 0 0 1px rgba(23,184,147,0.25), 0 0 24px -4px rgba(23,184,147,0.35)",
      },
      backgroundImage: {
        "grid-fade":
          "linear-gradient(to bottom, rgba(23,184,147,0.06), transparent 60%)",
      },
      animation: {
        "tick-in": "tickIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) both",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        tickIn: {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
}
