import { useEffect, useRef } from "react";
import { Animated, Easing, View } from "react-native";

import { styles } from "./ThinkingDots.style";

const DOT_COUNT = 3;
const PULSE_DURATION = 900;

export function ThinkingDots() {
  const animations = useRef(
    Array.from({ length: DOT_COUNT }, () => new Animated.Value(0)),
  ).current;

  useEffect(() => {
    const loops = animations.map((value, index) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(index * (PULSE_DURATION / DOT_COUNT)),
          Animated.timing(value, {
            toValue: 1,
            duration: PULSE_DURATION / 2,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(value, {
            toValue: 0,
            duration: PULSE_DURATION / 2,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
        ]),
      ),
    );
    for (const loop of loops) loop.start();
    return () => {
      for (const loop of loops) loop.stop();
    };
  }, [animations]);

  return (
    <View style={styles.row}>
      {animations.map((value, i) => (
        <Animated.View
          key={i}
          style={[
            styles.dot,
            {
              opacity: value.interpolate({
                inputRange: [0, 1],
                outputRange: [0.4 + i * 0.15, 1],
              }),
            },
          ]}
        />
      ))}
    </View>
  );
}
