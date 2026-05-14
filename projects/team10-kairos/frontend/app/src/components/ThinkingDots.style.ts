import { StyleSheet } from "react-native";

import { colors } from "../constants/theme";

export const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    gap: 5,
    paddingVertical: 6,
    paddingHorizontal: 2,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: colors.muted2,
  },
});
