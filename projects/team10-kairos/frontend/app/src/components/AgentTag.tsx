import { Text, View } from "react-native";

import { styles } from "./AgentTag.style";
import { KIcon } from "./KIcon";

type Props = {
  status?: string;
};

export function AgentTag({ status }: Props) {
  return (
    <View style={styles.row}>
      <View style={styles.avatar}>
        <KIcon name="sparkle-fill" size={11} color="#ffffff" />
      </View>
      <Text style={styles.name}>Kairos</Text>
      {status ? <Text style={styles.status}>{` · ${status}`}</Text> : null}
    </View>
  );
}
