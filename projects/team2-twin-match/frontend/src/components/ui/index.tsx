"use client";

/**
 * twinmatch UI primitives — 시안(AI 교육 Remix)에서 이식한 디자인 시스템.
 * 인라인 스타일 그대로 유지(시안 일관성). 색·반경·그림자 토큰은 globals.css.
 */

import type { CSSProperties, ReactNode } from "react";

// ──────────────────────────────────────────────────────────────
// Logo
// ──────────────────────────────────────────────────────────────

export const Logo = ({
  size = 32,
  color,
}: {
  size?: number;
  color?: string;
}) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <defs>
        <linearGradient id="lgo" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#FF5864" />
          <stop offset="1" stopColor="#FD267A" />
        </linearGradient>
      </defs>
      <path
        d="M11 8c-2.8 0-5 2.2-5 5 0 4.5 5.5 8.5 9 11 3.5-2.5 9-6.5 9-11 0-2.8-2.2-5-5-5-1.6 0-3 .8-4 2-1-1.2-2.4-2-4-2z"
        fill="url(#lgo)"
      />
      <circle cx="22" cy="10" r="2.2" fill="#fff" opacity=".55" />
    </svg>
    <span
      style={{
        fontFamily: "var(--font-serif)",
        fontSize: size * 0.78,
        fontStyle: "italic",
        color: color || "var(--ink)",
        letterSpacing: -0.5,
        lineHeight: 1,
      }}
    >
      twinmatch
    </span>
  </span>
);

// ──────────────────────────────────────────────────────────────
// Avatar
// ──────────────────────────────────────────────────────────────

export type AvatarGradient =
  | "coral"
  | "peach"
  | "sunset"
  | "plum"
  | "cream"
  | "teal";

const AVATAR_GRADIENTS: Record<AvatarGradient, string> = {
  coral: "linear-gradient(135deg,#FF5864 0%,#FD267A 100%)",
  peach: "linear-gradient(135deg,#FFB199 0%,#FF6B6B 100%)",
  sunset: "linear-gradient(135deg,#FFD86F 0%,#FB6786 100%)",
  plum: "linear-gradient(135deg,#A78BFA 0%,#FD267A 100%)",
  cream: "linear-gradient(135deg,#FFE4D6 0%,#FFB199 100%)",
  teal: "linear-gradient(135deg,#7BD7C8 0%,#3AB0A0 100%)",
};

export const Avatar = ({
  name,
  gradient = "coral",
  size = 56,
  ring = false,
  char,
}: {
  name?: string;
  gradient?: AvatarGradient;
  size?: number;
  ring?: boolean;
  char?: string;
}) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: "50%",
      background: AVATAR_GRADIENTS[gradient],
      display: "grid",
      placeItems: "center",
      color: "white",
      fontWeight: 700,
      fontSize: size * 0.36,
      boxShadow: ring
        ? "0 0 0 4px var(--cream), 0 0 0 6px rgba(255,88,100,.45)"
        : "var(--shadow-sm)",
      flexShrink: 0,
      position: "relative",
      letterSpacing: -0.5,
    }}
  >
    {char || (name ? name[0] : "?")}
  </div>
);

// ──────────────────────────────────────────────────────────────
// Pill
// ──────────────────────────────────────────────────────────────

export type PillTone = "cream" | "coral" | "line" | "dark" | "ok";

const PILL_TONES: Record<PillTone, { bg: string; fg: string; bd: string }> = {
  cream: { bg: "var(--cream-2)", fg: "var(--ink-soft)", bd: "transparent" },
  coral: {
    bg: "rgba(255,88,100,.12)",
    fg: "var(--coral-deep)",
    bd: "transparent",
  },
  line: { bg: "transparent", fg: "var(--ink-soft)", bd: "var(--line)" },
  dark: { bg: "var(--ink)", fg: "white", bd: "transparent" },
  ok: { bg: "rgba(54,179,126,.12)", fg: "var(--ok)", bd: "transparent" },
};

export const Pill = ({
  children,
  tone = "cream",
  size = "md",
  icon,
}: {
  children: ReactNode;
  tone?: PillTone;
  size?: "sm" | "md";
  icon?: ReactNode;
}) => {
  const t = PILL_TONES[tone];
  const sz = size === "sm" ? { p: "4px 10px", f: 12 } : { p: "6px 12px", f: 13 };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: sz.p,
        borderRadius: 99,
        background: t.bg,
        color: t.fg,
        border: `1px solid ${t.bd}`,
        fontSize: sz.f,
        fontWeight: 500,
        whiteSpace: "nowrap",
      }}
    >
      {icon}
      {children}
    </span>
  );
};

// ──────────────────────────────────────────────────────────────
// Btn
// ──────────────────────────────────────────────────────────────

export type BtnVariant = "primary" | "dark" | "ghost" | "soft";
export type BtnSize = "sm" | "md" | "lg" | "xl";

const BTN_SIZES: Record<BtnSize, { p: string; f: number; r: number }> = {
  sm: { p: "8px 14px", f: 14, r: 10 },
  md: { p: "12px 22px", f: 15, r: 12 },
  lg: { p: "16px 28px", f: 16, r: 14 },
  xl: { p: "20px 36px", f: 17, r: 16 },
};

const BTN_VARIANTS: Record<
  BtnVariant,
  { bg: string; fg: string; sh: string; bd: string }
> = {
  primary: {
    bg: "linear-gradient(135deg,#FF5864 0%,#FD267A 100%)",
    fg: "white",
    sh: "var(--shadow-pop)",
    bd: "none",
  },
  dark: { bg: "var(--ink)", fg: "white", sh: "var(--shadow-md)", bd: "none" },
  ghost: {
    bg: "transparent",
    fg: "var(--ink)",
    sh: "none",
    bd: "1px solid var(--line)",
  },
  soft: {
    bg: "white",
    fg: "var(--ink)",
    sh: "var(--shadow-sm)",
    bd: "1px solid var(--line)",
  },
};

export const Btn = ({
  children,
  variant = "primary",
  size = "md",
  onClick,
  disabled,
  full,
  icon,
  style,
  type,
}: {
  children?: ReactNode;
  variant?: BtnVariant;
  size?: BtnSize;
  onClick?: () => void;
  disabled?: boolean;
  full?: boolean;
  icon?: ReactNode;
  style?: CSSProperties;
  type?: "button" | "submit" | "reset";
}) => {
  const v = BTN_VARIANTS[variant];
  const s = BTN_SIZES[size];
  return (
    <button
      type={type || "button"}
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: s.p,
        borderRadius: s.r,
        background: v.bg,
        color: v.fg,
        boxShadow: v.sh,
        border: v.bd,
        fontSize: s.f,
        fontWeight: 600,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        width: full ? "100%" : undefined,
        opacity: disabled ? 0.5 : 1,
        transition: "transform .15s ease, box-shadow .15s ease, opacity .15s",
        cursor: disabled ? "not-allowed" : "pointer",
        letterSpacing: -0.2,
        ...style,
      }}
      onMouseDown={(e) => {
        if (!disabled) e.currentTarget.style.transform = "translateY(1px)";
      }}
      onMouseUp={(e) => (e.currentTarget.style.transform = "")}
      onMouseLeave={(e) => (e.currentTarget.style.transform = "")}
    >
      {children}
      {icon}
    </button>
  );
};

// ──────────────────────────────────────────────────────────────
// Icon (lucide-style 라인)
// ──────────────────────────────────────────────────────────────

type IconFn = (size?: number, fill?: string) => ReactNode;

export const Icon: Record<
  | "arrowRight"
  | "arrowLeft"
  | "sparkles"
  | "heart"
  | "check"
  | "x"
  | "info"
  | "copy"
  | "message"
  | "shield",
  IconFn
> = {
  arrowRight: (s = 18) => (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  ),
  arrowLeft: (s = 18) => (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 12H5M11 6l-6 6 6 6" />
    </svg>
  ),
  sparkles: (s = 18) => (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v3m0 12v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" />
    </svg>
  ),
  heart: (s = 18, fill = "none") => (
    <svg width={s} height={s} viewBox="0 0 24 24" fill={fill} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  ),
  check: (s = 18) => (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12l5 5L20 7" />
    </svg>
  ),
  x: (s = 18) => (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  ),
  info: (s = 18) => (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
  ),
  copy: (s = 16) => (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  ),
  message: (s = 18) => (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  shield: (s = 18) => (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
};

// ──────────────────────────────────────────────────────────────
// TopNav
// ──────────────────────────────────────────────────────────────

export const TopNav = ({
  onLogo,
  step,
  totalSteps,
  onRestart,
}: {
  onLogo?: () => void;
  step?: number | null;
  totalSteps?: number;
  onRestart?: (() => void) | null;
}) => (
  <header
    style={{
      height: 72,
      padding: "0 48px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      background: "rgba(255,248,244,.85)",
      backdropFilter: "blur(12px)",
      borderBottom: "1px solid var(--line)",
      position: "sticky",
      top: 0,
      zIndex: 50,
    }}
  >
    <button onClick={onLogo} style={{ cursor: "pointer" }}>
      <Logo size={28} />
    </button>
    {step != null && totalSteps != null && (
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {Array.from({ length: totalSteps }).map((_, i) => (
          <div
            key={i}
            style={{
              width: i === step ? 28 : 8,
              height: 8,
              borderRadius: 99,
              background: i <= step ? "var(--coral)" : "var(--line)",
              transition: "all .35s cubic-bezier(.2,.8,.2,1)",
            }}
          />
        ))}
      </div>
    )}
    <nav
      style={{
        display: "flex",
        gap: 8,
        alignItems: "center",
        color: "var(--ink-soft)",
        fontSize: 14,
      }}
    >
      <a style={{ padding: "8px 12px", color: "inherit", textDecoration: "none" }}>How it works</a>
      <a style={{ padding: "8px 12px", color: "inherit", textDecoration: "none" }}>Stories</a>
      <a style={{ padding: "8px 12px", color: "inherit", textDecoration: "none" }}>FAQ</a>
      {onRestart && (
        <Btn variant="soft" size="sm" onClick={onRestart}>
          처음부터
        </Btn>
      )}
    </nav>
  </header>
);

// ──────────────────────────────────────────────────────────────
// Card
// ──────────────────────────────────────────────────────────────

export const Card = ({
  children,
  style,
  pad = 32,
}: {
  children: ReactNode;
  style?: CSSProperties;
  pad?: number;
}) => (
  <div
    style={{
      background: "white",
      border: "1px solid var(--line)",
      borderRadius: "var(--r-lg)",
      padding: pad,
      boxShadow: "var(--shadow-sm)",
      transition: "transform .25s ease, box-shadow .25s ease",
      ...style,
    }}
  >
    {children}
  </div>
);
