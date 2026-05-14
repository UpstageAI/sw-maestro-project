import type { ReactNode } from "react";
import { Text, View } from "react-native";

import { colors, shadow } from "../constants/theme";
import { KIcon, type KIconName } from "./KIcon";
import { styles } from "./ScheduleCard.style";

type Props = {
  title: string;
  date: string;
  time?: string;
  place?: string;
  alarm?: string;
  accent?: string;
  compact?: boolean;
  extra?: ReactNode;
};

export function ScheduleCard({
  title,
  date,
  time,
  place,
  alarm,
  accent = colors.indigo,
  compact = false,
  extra,
}: Props) {
  return (
    <View
      style={[
        styles.card,
        compact && styles.cardCompact,
        shadow.sm,
      ]}
    >
      <View style={[styles.header, { marginBottom: compact ? 10 : 14 }]}>
        <View style={[styles.accentBar, { backgroundColor: accent }]} />
        <View style={{ flex: 1 }}>
          <Text style={styles.kicker}>등록할 일정</Text>
          <Text style={[styles.title, compact ? styles.titleCompact : null]}>
            {title}
          </Text>
        </View>
      </View>

      <View style={[styles.rows, { gap: compact ? 8 : 10 }]}>
        <Row icon="calendar" label="날짜" value={date} />
        {time ? <Row icon="clock" label="시간" value={time} /> : null}
        {place ? <Row icon="pin" label="장소" value={place} /> : null}
        {alarm ? (
          <Row
            icon="bell"
            label="알림"
            value={alarm}
            hint={alarm.startsWith("기본") ? "변경" : undefined}
          />
        ) : null}
        {extra}
      </View>
    </View>
  );
}

function Row({
  icon,
  label,
  value,
  hint,
}: {
  icon: KIconName;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <View style={styles.row}>
      <View style={styles.rowIcon}>
        <KIcon name={icon} size={15} color={colors.muted2} />
      </View>
      <Text style={styles.rowLabel}>{label}</Text>
      <View style={styles.rowValueWrap}>
        <Text style={styles.rowValue}>{value}</Text>
        {hint ? <Text style={styles.rowHint}>{`·  ${hint}`}</Text> : null}
      </View>
    </View>
  );
}
