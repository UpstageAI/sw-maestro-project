import { StyleSheet } from "react-native";

import { radii } from "../constants/theme";

export const styles = StyleSheet.create({
  button: {
    borderRadius: radii.pill,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
  },
  label: {
    fontWeight: "600",
    letterSpacing: -0.14,
  },
});
