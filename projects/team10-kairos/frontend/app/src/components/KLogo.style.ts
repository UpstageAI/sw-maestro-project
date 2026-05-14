import { StyleSheet } from "react-native";

import { colors } from "../constants/theme";

export const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
  },
  mark: {
    backgroundColor: colors.indigo,
    alignItems: "center",
    justifyContent: "center",
  },
  wordmark: {
    fontWeight: "700",
    letterSpacing: -0.6,
  },
});
