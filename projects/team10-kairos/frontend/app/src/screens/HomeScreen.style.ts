import { StyleSheet } from "react-native";

import { colors, radii } from "../constants/theme";

export const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.cream,
  },
  scrollContent: {
    paddingBottom: 32,
  },
  topBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  avatarButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.mist,
    alignItems: "center",
    justifyContent: "center",
  },
  heroHeader: {
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 12,
  },
  heroSubtitle: {
    fontSize: 12,
    fontWeight: "500",
    color: colors.muted,
    marginBottom: 4,
  },
  heroTitle: {
    fontSize: 28,
    fontWeight: "700",
    letterSpacing: -1,
    lineHeight: 32,
    color: colors.ink,
  },
  heroCard: {
    marginHorizontal: 20,
    backgroundColor: colors.paper,
    borderRadius: 24,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.line2,
  },
  heroCardKicker: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
  },
  heroCardKickerText: {
    fontSize: 12,
    fontWeight: "600",
    color: colors.indigo,
  },
  heroInput: {
    fontSize: 17,
    lineHeight: 25,
    color: colors.ink,
    fontWeight: "400",
    minHeight: 92,
    padding: 0,
    textAlignVertical: "top",
  },
  heroCardFooter: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 10,
  },
  heroFooterLeft: {
    flexDirection: "row",
    gap: 6,
  },
  heroFooterCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.cream2,
    alignItems: "center",
    justifyContent: "center",
  },
  submitButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.ink,
    alignItems: "center",
    justifyContent: "center",
  },
  suggestionWrap: {
    paddingHorizontal: 20,
    paddingTop: 16,
  },
  suggestionLabel: {
    fontSize: 12,
    color: colors.muted,
    fontWeight: "500",
    marginBottom: 9,
    paddingLeft: 4,
  },
  suggestionChips: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 7,
  },
  todayWrap: {
    paddingHorizontal: 20,
    paddingTop: 26,
  },
  todayHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: 10,
  },
  todayHeaderLabel: {
    fontSize: 13,
    color: colors.muted,
    fontWeight: "600",
  },
  todayHeaderLink: {
    fontSize: 12,
    color: colors.indigo,
    fontWeight: "600",
  },
  emptyText: {
    fontSize: 13,
    color: colors.muted2,
    paddingVertical: 14,
    paddingHorizontal: 4,
  },
  todayRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingVertical: 11,
    paddingHorizontal: 12,
    borderRadius: radii.md - 2,
    borderBottomWidth: 1,
    borderBottomColor: colors.line2,
  },
  todayRowTime: {
    fontVariant: ["tabular-nums"],
    fontSize: 13,
    fontWeight: "600",
    color: colors.ink2,
    width: 56,
  },
  todayRowBody: {
    flex: 1,
  },
  todayRowTitle: {
    fontSize: 14.5,
    fontWeight: "600",
    color: colors.ink,
    letterSpacing: -0.14,
  },
  todayRowMeta: {
    fontSize: 11.5,
    color: colors.muted2,
    marginTop: 1,
  },
  todayRowTag: {
    paddingHorizontal: 9,
    paddingVertical: 3,
    borderRadius: 999,
  },
  todayRowTagText: {
    fontSize: 11,
    fontWeight: "600",
  },
});
