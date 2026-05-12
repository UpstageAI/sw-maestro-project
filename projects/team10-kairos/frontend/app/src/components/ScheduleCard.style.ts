import { StyleSheet } from "react-native";

import { colors, radii } from "../constants/theme";

export const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.paper,
    borderRadius: radii.lg - 2,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.line2,
  },
  cardCompact: {
    padding: 14,
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  accentBar: {
    width: 4,
    alignSelf: "stretch",
    borderRadius: 2,
    marginVertical: 4,
  },
  kicker: {
    fontSize: 11,
    color: colors.muted,
    fontWeight: "500",
    marginBottom: 4,
  },
  title: {
    fontSize: 18,
    fontWeight: "600",
    color: colors.ink,
    letterSpacing: -0.36,
    lineHeight: 22,
  },
  titleCompact: {
    fontSize: 16,
    lineHeight: 20,
  },
  rows: {
    flexDirection: "column",
    paddingLeft: 14,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  rowIcon: {
    width: 18,
    alignItems: "center",
    justifyContent: "center",
  },
  rowLabel: {
    width: 38,
    color: colors.muted,
    fontSize: 12,
    fontWeight: "500",
  },
  rowValueWrap: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
  },
  rowValue: {
    color: colors.ink,
    fontSize: 13.5,
    fontWeight: "500",
  },
  rowHint: {
    color: colors.muted2,
    fontSize: 12,
    fontWeight: "400",
    marginLeft: 6,
  },
});
