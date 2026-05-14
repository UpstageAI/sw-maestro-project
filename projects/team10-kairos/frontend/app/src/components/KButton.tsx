import type { ReactNode } from "react";
import {
  Pressable,
  type PressableProps,
  Text,
  type ViewStyle,
} from "react-native";

import { colors } from "../constants/theme";
import { styles } from "./KButton.style";
import { KIcon, type KIconName } from "./KIcon";

type Variant = "primary" | "coral" | "ghost" | "light";
type Size = "sm" | "md" | "lg";

type Props = {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  icon?: KIconName;
  full?: boolean;
  style?: ViewStyle;
} & Omit<PressableProps, "children" | "style">;

const VARIANT_STYLES: Record<
  Variant,
  { bg: string; fg: string; border?: string }
> = {
  primary: { bg: colors.ink, fg: colors.cream },
  coral: { bg: colors.indigo, fg: "#ffffff" },
  ghost: { bg: colors.mist, fg: colors.ink },
  light: { bg: colors.paper, fg: colors.ink, border: colors.line2 },
};

const SIZE_STYLES: Record<
  Size,
  { height: number; paddingHorizontal: number; fontSize: number; iconSize: number }
> = {
  sm: { height: 36, paddingHorizontal: 14, fontSize: 13, iconSize: 14 },
  md: { height: 44, paddingHorizontal: 18, fontSize: 14.5, iconSize: 16 },
  lg: { height: 52, paddingHorizontal: 22, fontSize: 15.5, iconSize: 18 },
};

export function KButton({
  children,
  variant = "primary",
  size = "md",
  icon,
  full = false,
  style,
  ...rest
}: Props) {
  const v = VARIANT_STYLES[variant];
  const s = SIZE_STYLES[size];

  return (
    <Pressable
      {...rest}
      style={({ pressed }) => [
        styles.button,
        {
          height: s.height,
          paddingHorizontal: s.paddingHorizontal,
          backgroundColor: v.bg,
          borderWidth: v.border ? 1 : 0,
          borderColor: v.border,
          alignSelf: full ? "stretch" : "flex-start",
          opacity: pressed ? 0.85 : 1,
        },
        style,
      ]}
    >
      {icon ? <KIcon name={icon} size={s.iconSize} color={v.fg} /> : null}
      <Text style={[styles.label, { color: v.fg, fontSize: s.fontSize }]}>
        {children}
      </Text>
    </Pressable>
  );
}
