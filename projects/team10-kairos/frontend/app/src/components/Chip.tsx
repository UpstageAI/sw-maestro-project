import type { ReactNode } from "react";
import { Pressable, type PressableProps, Text } from "react-native";

import { colors } from "../constants/theme";
import { styles } from "./Chip.style";

type Props = {
  children: ReactNode;
  accent?: boolean;
} & Omit<PressableProps, "children" | "style">;

export function Chip({ children, accent = false, ...rest }: Props) {
  return (
    <Pressable
      {...rest}
      style={[
        styles.chip,
        {
          backgroundColor: accent ? colors.indigo50 : colors.paper,
          borderColor: accent ? colors.indigo100 : colors.line2,
        },
      ]}
    >
      <Text
        style={[styles.label, { color: accent ? colors.indigo : colors.ink2 }]}
      >
        {children}
      </Text>
    </Pressable>
  );
}
