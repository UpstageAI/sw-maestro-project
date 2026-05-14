import { StyleSheet } from "react-native";

const DAY_DISC_SIZE = 30;

export const styles = StyleSheet.create({
  root: {
    width: "100%",
  },
  dowRow: {
    flexDirection: "row",
    marginBottom: 6,
    paddingHorizontal: 2,
  },
  dowCell: {
    flex: 1,
    alignItems: "center",
  },
  dowText: {
    fontSize: 11,
    fontWeight: "500",
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  cell: {
    width: `${100 / 7}%`,
    alignItems: "center",
    paddingTop: 4,
  },
  dayDisc: {
    width: DAY_DISC_SIZE,
    height: DAY_DISC_SIZE,
    borderRadius: DAY_DISC_SIZE / 2,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  dayText: {
    fontVariant: ["tabular-nums"],
  },
  markRow: {
    flexDirection: "row",
    gap: 2,
    marginTop: 2,
  },
  markDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
  },
});
