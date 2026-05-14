export const colors = {
  cream: "#eef0f3",
  cream2: "#e6e9ee",
  paper: "#ffffff",
  mist: "#dde0e6",
  line: "#dde0e6",
  line2: "#e4e7ec",
  ink: "#181a22",
  ink2: "#262a35",
  muted: "#6a6e7a",
  muted2: "#9aa0a8",
  faint: "#c1c5cc",
  indigo: "#3d4ed8",
  indigoPressed: "#2f3eb8",
  indigo50: "#e6e9ff",
  indigo100: "#c8cffc",
  indigoTint: "#dde2ff",
  coral: "#3d4ed8",
  coralPressed: "#2f3eb8",
  coral50: "#e6e9ff",
  coral100: "#c8cffc",
  coralTint: "#dde2ff",
  pink: "#c45a8b",
  pink50: "#fbeaf1",
  pink100: "#f3cedd",
  pinkTint: "#f7dde7",
  mint: "#c8d9d2",
  mintTint: "#e2ece8",
  sage: "#c8d9d2",
  sageTint: "#e2ece8",
  sky: "#c8d4e8",
  skyTint: "#e0e7f0",
  lilac: "#d8d2e8",
  lilacTint: "#ebe7f3",
  butter: "#d8d2e8",
  butterTint: "#ebe7f3",
  success: "#2e8a5e",
  warn: "#b97d2c",
  danger: "#c4392e",
  deadline: "#c45a8b",
};

export const spacing = {
  screen: 20,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
};

export const radii = {
  xs: 8,
  sm: 12,
  md: 16,
  lg: 22,
  xl: 28,
  pill: 999,
};

export const shadow = {
  sm: {
    shadowColor: "rgba(24,26,34,1)",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 1,
  },
  md: {
    shadowColor: "rgba(24,26,34,1)",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.07,
    shadowRadius: 20,
    elevation: 2,
  },
  lg: {
    shadowColor: "rgba(24,26,34,1)",
    shadowOffset: { width: 0, height: 24 },
    shadowOpacity: 0.12,
    shadowRadius: 60,
    elevation: 4,
  },
};

export const typography = {
  display: { fontSize: 28, fontWeight: "700" as const, letterSpacing: -1 },
  heading: { fontSize: 22, fontWeight: "600" as const, letterSpacing: -0.55 },
  body: { fontSize: 16, fontWeight: "500" as const, letterSpacing: -0.16 },
  caption: { fontSize: 13, fontWeight: "400" as const },
};
