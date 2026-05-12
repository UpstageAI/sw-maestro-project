import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    // Reset color palette entirely — Airbnb DESIGN.md tokens only.
    colors: {
      transparent: "transparent",
      current: "currentColor",
      white: "#ffffff",
      black: "#000000",

      // Brand & accent
      rausch: {
        DEFAULT: "#ff385c",
        active: "#e00b41",
        disabled: "#ffd1da",
      },
      luxe: "#460479",
      plus: "#92174d",

      // Text
      ink: "#222222",
      body: "#3f3f3f",
      muted: "#6a6a6a",
      "muted-soft": "#929292",

      // Hairlines & borders
      hairline: "#dddddd",
      "hairline-soft": "#ebebeb",
      "border-strong": "#c1c1c1",

      // Surfaces
      canvas: "#ffffff",
      "surface-soft": "#f7f7f7",
      "surface-strong": "#f2f2f2",

      // Inverted text
      "on-primary": "#ffffff",
      "on-dark": "#ffffff",

      // Semantic
      "error-text": "#c13515",
      "error-text-hover": "#b32505",
      "legal-link": "#428bff",
    },

    // Airbnb radius scale.
    borderRadius: {
      none: "0px",
      xs: "4px",
      sm: "8px",
      DEFAULT: "8px",
      md: "14px",
      lg: "20px",
      xl: "32px",
      full: "9999px",
    },

    // Airbnb spacing scale (4px base, 2px micro-step).
    spacing: {
      0: "0px",
      px: "1px",
      xxs: "2px",
      xs: "4px",
      sm: "8px",
      md: "12px",
      base: "16px",
      lg: "24px",
      xl: "32px",
      xxl: "48px",
      section: "64px",
      // Numeric aliases used by Tailwind defaults that we still need
      0.5: "2px",
      1: "4px",
      1.5: "6px",
      2: "8px",
      2.5: "10px",
      3: "12px",
      3.5: "14px",
      4: "16px",
      5: "20px",
      6: "24px",
      7: "28px",
      8: "32px",
      9: "36px",
      10: "40px",
      11: "44px",
      12: "48px",
      14: "56px",
      16: "64px",
      18: "72px",
      20: "80px",
      24: "96px",
      28: "112px",
      32: "128px",
      36: "144px",
      40: "160px",
      48: "192px",
      56: "224px",
      64: "256px",
      72: "288px",
      80: "320px",
    },

    extend: {
      colors: {
        // Status pills for material cards — low-saturation semantic colors.
        // These don't conflict with Airbnb tokens (no emerald/amber/rose in that palette).
        emerald: {
          50: "#f0fdf4",
          700: "#15803d",
        },
        amber: {
          50: "#fffbeb",
          400: "#fbbf24",
          700: "#b45309",
        },
        rose: {
          50: "#fff1f2",
          700: "#be123c",
        },
      },
      fontFamily: {
        // DESIGN.md: Inter is the closest open-source substitute for Cereal VF.
        sans: [
          "'Airbnb Cereal VF'",
          "Circular",
          "Inter",
          "-apple-system",
          "system-ui",
          "Roboto",
          "Helvetica Neue",
          "sans-serif",
        ],
      },
      fontSize: {
        // Airbnb typography scale — token name → [size, { lineHeight, letterSpacing, fontWeight }]
        "rating-display": ["64px", { lineHeight: "1.1", letterSpacing: "-1px", fontWeight: "700" }],
        "display-xl": ["28px", { lineHeight: "1.43", letterSpacing: "0", fontWeight: "700" }],
        "display-lg": ["22px", { lineHeight: "1.18", letterSpacing: "-0.44px", fontWeight: "500" }],
        "display-md": ["21px", { lineHeight: "1.43", letterSpacing: "0", fontWeight: "700" }],
        "display-sm": ["20px", { lineHeight: "1.20", letterSpacing: "-0.18px", fontWeight: "600" }],
        "title-md": ["16px", { lineHeight: "1.25", letterSpacing: "0", fontWeight: "600" }],
        "title-sm": ["16px", { lineHeight: "1.25", letterSpacing: "0", fontWeight: "500" }],
        "body-md": ["16px", { lineHeight: "1.5", letterSpacing: "0", fontWeight: "400" }],
        "body-sm": ["14px", { lineHeight: "1.43", letterSpacing: "0", fontWeight: "400" }],
        caption: ["14px", { lineHeight: "1.29", letterSpacing: "0", fontWeight: "500" }],
        "caption-sm": ["13px", { lineHeight: "1.23", letterSpacing: "0", fontWeight: "400" }],
        badge: ["11px", { lineHeight: "1.18", letterSpacing: "0", fontWeight: "600" }],
        "micro-label": ["12px", { lineHeight: "1.33", letterSpacing: "0", fontWeight: "700" }],
        "uppercase-tag": ["8px", { lineHeight: "1.25", letterSpacing: "0.32px", fontWeight: "700" }],
        "button-md": ["16px", { lineHeight: "1.25", letterSpacing: "0", fontWeight: "500" }],
        "button-sm": ["14px", { lineHeight: "1.29", letterSpacing: "0", fontWeight: "500" }],
        "nav-link": ["16px", { lineHeight: "1.25", letterSpacing: "0", fontWeight: "600" }],
        link: ["14px", { lineHeight: "1.43", letterSpacing: "0", fontWeight: "400" }],
      },
      boxShadow: {
        // The single Airbnb elevation tier — used on hover-floated cards and dropdowns.
        airbnb:
          "rgba(0, 0, 0, 0.02) 0 0 0 1px, rgba(0, 0, 0, 0.04) 0 2px 6px 0, rgba(0, 0, 0, 0.10) 0 4px 8px 0",
      },
      maxWidth: {
        "screen-2xl": "1536px",
        airbnb: "1280px",
        listing: "1080px",
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};

export default config;
