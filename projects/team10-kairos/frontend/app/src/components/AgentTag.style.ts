import { StyleSheet } from "react-native";

import { colors } from "../constants/theme";

export const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginVertical: 2,
    marginHorizontal: 4,
    marginBottom: 6,
  },
  avatar: {
    width: 18,
    height: 18,
    borderRadius: 6,
    backgroundColor: colors.indigo,
    alignItems: "center",
    justifyContent: "center",
  },
  name: {
    fontSize: 12,
    fontWeight: "500",
    color: colors.muted,
  },
  status: {
    fontSize: 12,
    color: colors.muted2,
    fontWeight: "500",
  },
});
