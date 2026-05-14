import { StyleSheet } from "react-native";

import { colors, radii } from "../constants/theme";

export const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.cream,
  },
  topBar: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  topYear: {
    fontSize: 12,
    color: colors.muted,
    fontWeight: "500",
  },
  topMonth: {
    fontSize: 24,
    fontWeight: "700",
    letterSpacing: -0.72,
    color: colors.ink,
  },
  topActions: {
    flexDirection: "row",
    gap: 8,
  },
  topActionBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.cream2,
    alignItems: "center",
    justifyContent: "center",
  },
  calendarWrap: {
    paddingHorizontal: 14,
    paddingTop: 8,
  },
  daySheet: {
    flex: 1,
    marginTop: 8,
    backgroundColor: colors.paper,
    borderTopLeftRadius: radii.xl - 4,
    borderTopRightRadius: radii.xl - 4,
    borderTopWidth: 1,
    borderTopColor: colors.line2,
  },
  daySheetHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 12,
  },
  daySheetSubtitle: {
    fontSize: 12,
    color: colors.muted,
    fontWeight: "500",
  },
  daySheetTitle: {
    fontSize: 18,
    fontWeight: "700",
    letterSpacing: -0.36,
    color: colors.ink,
  },
  newBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: colors.indigo50,
  },
  newBadgeText: {
    fontSize: 12,
    fontWeight: "600",
    color: colors.indigo,
  },
  daySheetList: {
    paddingHorizontal: 16,
    paddingBottom: 24,
  },
  emptyText: {
    fontSize: 13,
    color: colors.muted2,
    fontStyle: "italic",
    textAlign: "center",
    paddingVertical: 32,
  },
  dayItem: {
    flexDirection: "row",
    alignItems: "stretch",
    gap: 12,
    padding: 12,
    borderRadius: 16,
    marginBottom: 8,
    borderWidth: 1,
  },
  dayItemBar: {
    width: 3,
    borderRadius: 2,
  },
  dayItemTime: {
    fontVariant: ["tabular-nums"],
    fontSize: 12,
    color: colors.muted,
    fontWeight: "600",
    width: 38,
    paddingTop: 1,
  },
  dayItemTitle: {
    fontSize: 14.5,
    fontWeight: "600",
    letterSpacing: -0.14,
    color: colors.ink,
  },
  dayItemMetaRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 2,
  },
  dayItemMeta: {
    fontSize: 12,
    color: colors.muted,
  },
  dayItemAlarm: {
    fontSize: 12,
    color: colors.indigo,
  },
});
