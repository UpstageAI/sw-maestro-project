import { StyleSheet } from "react-native";

import { radii } from "../constants/theme";

export const styles = StyleSheet.create({
  chip: {
    paddingVertical: 8,
    paddingHorizontal: 13,
    borderRadius: radii.pill,
    borderWidth: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "flex-start",
  },
  label: {
    fontSize: 13,
    fontWeight: "500",
    letterSpacing: -0.13,
  },
});
