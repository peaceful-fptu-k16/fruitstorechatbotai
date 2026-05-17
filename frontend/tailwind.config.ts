import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Explicit hex so Tailwind opacity modifiers (bg-accent/20) work correctly
        canvas:        "#fdf6ec",
        surface:       "#ffffff",
        ink:           "#1a0f00",
        "ink-soft":    "#7a5c38",
        accent:        "#f06322",
        "accent-2":    "#f5a623",
        "accent-light":"#ffe9dd",
        leaf:          "#2d9555",
        "leaf-light":  "#e5f7ed",
        mellow:        "#fff3de",
        berry:         "#c0392b",
        rind:          "#5b8e2d",
      },
      fontFamily: {
        body:  ["var(--font-body)",  "Be Vietnam Pro", "sans-serif"],
        title: ["var(--font-title)", "Playfair Display", "serif"],
      },
      boxShadow: {
        float:       "0 20px 60px -15px rgba(240,99,34,0.28), 0 4px 16px rgba(240,99,34,0.08)",
        card:        "0 4px 24px -6px rgba(26,15,0,0.10), 0 1px 4px rgba(26,15,0,0.05)",
        "card-hover":"0 16px 48px -12px rgba(240,99,34,0.22), 0 4px 16px rgba(26,15,0,0.08)",
        glow:        "0 0 22px rgba(240,99,34,0.50)",
        "glow-leaf": "0 0 22px rgba(45,149,85,0.40)",
      },
      keyframes: {
        rise: {
          "0%":   { opacity: "0", transform: "translateY(20px) scale(0.97)" },
          "100%": { opacity: "1", transform: "translateY(0)   scale(1)"    },
        },
        scaleIn: {
          "0%":   { opacity: "0", transform: "scale(0.86)" },
          "100%": { opacity: "1", transform: "scale(1)"    },
        },
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        pulseDot: {
          "0%, 100%": { transform: "translateY(0)",   opacity: "0.40" },
          "50%":      { transform: "translateY(-6px)", opacity: "1"    },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% center" },
          "100%": { backgroundPosition:  "200% center" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)   rotate(0deg)"  },
          "33%":      { transform: "translateY(-14px) rotate(5deg)"  },
          "66%":      { transform: "translateY(-7px)  rotate(-3deg)" },
        },
        blobMove: {
          "0%":   { transform: "translate(0,0)    scale(1)"    },
          "33%":  { transform: "translate(40px,-60px) scale(1.08)" },
          "66%":  { transform: "translate(-20px,25px) scale(0.94)" },
          "100%": { transform: "translate(0,0)    scale(1)"    },
        },
      },
      animation: {
        rise:     "rise     460ms cubic-bezier(0.16,1,0.3,1) both",
        scaleIn:  "scaleIn  360ms cubic-bezier(0.16,1,0.3,1) both",
        fadeIn:   "fadeIn   500ms ease-out both",
        pulseDot: "pulseDot 1s   ease-in-out infinite",
        shimmer:  "shimmer  2s   linear     infinite",
        float:    "float    4s   ease-in-out infinite",
        blob:     "blobMove 12s  ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
