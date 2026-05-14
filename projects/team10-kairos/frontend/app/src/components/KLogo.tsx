import { Text, View } from "react-native";

import { colors } from "../constants/theme";
import { styles } from "./KLogo.style";

type Props = {
  size?: number;
  color?: string;
};

export function KLogo({ size = 20, color = colors.ink }: Props) {
  const dotSize = size * 0.42;
  const fontSize = size * 0.85;

  return (
    <View style={styles.row}>
      <View
        style={[
          styles.mark,
          {
            width: size,
            height: size,
            borderRadius: size * 0.42,
          },
        ]}
      >
        <View
          style={{
            width: dotSize,
            height: dotSize,
            borderRadius: dotSize / 2,
            backgroundColor: colors.cream,
          }}
        />
      </View>
      <Text style={[styles.wordmark, { color, fontSize }]}>kairos</Text>
    </View>
  );
}
