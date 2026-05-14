import type { ReactNode } from "react";
import { Text, View } from "react-native";

import { styles } from "./AgentBubble.style";

type Tone = "agent" | "user" | "system";

type Props = {
  children: ReactNode;
  tone?: Tone;
  small?: boolean;
};

export function AgentBubble({ children, tone = "agent", small = false }: Props) {
  const isAgent = tone === "agent";
  const isUser = tone === "user";
  const isSystem = tone === "system";

  const bubbleStyle = [
    styles.bubble,
    small ? styles.bubbleSmall : styles.bubbleMd,
    isAgent && styles.bubbleAgent,
    isUser && styles.bubbleUser,
    isSystem && styles.bubbleSystem,
  ];

  const textStyle = [styles.text, isUser && styles.textUser];

  return (
    <View
      style={[
        styles.container,
        { justifyContent: isUser ? "flex-end" : "flex-start" },
      ]}
    >
      <View style={bubbleStyle}>
        {typeof children === "string" ? (
          <Text style={textStyle}>{children}</Text>
        ) : (
          children
        )}
      </View>
    </View>
  );
}
