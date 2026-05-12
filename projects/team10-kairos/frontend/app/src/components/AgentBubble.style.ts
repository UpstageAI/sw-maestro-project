import { StyleSheet } from "react-native";

import { colors } from "../constants/theme";

export const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    width: "100%",
  },
  bubble: {
    maxWidth: "84%",
    borderRadius: 18,
  },
  bubbleSmall: {
    paddingVertical: 10,
    paddingHorizontal: 13,
  },
  bubbleMd: {
    paddingVertical: 13,
    paddingHorizontal: 15,
  },
  bubbleAgent: {
    backgroundColor: colors.paper,
    borderWidth: 1,
    borderColor: colors.line2,
    borderBottomLeftRadius: 6,
  },
  bubbleUser: {
    backgroundColor: colors.ink,
    borderBottomRightRadius: 6,
  },
  bubbleSystem: {
    backgroundColor: "transparent",
  },
  text: {
    fontSize: 14.5,
    lineHeight: 21,
    color: colors.ink,
    letterSpacing: -0.14,
  },
  textUser: {
    color: colors.cream,
  },
});
