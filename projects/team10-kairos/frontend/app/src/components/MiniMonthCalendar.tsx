import { Pressable, Text, View } from "react-native";

import { colors } from "../constants/theme";
import { styles } from "./MiniMonthCalendar.style";

export type DayMark = "indigo" | "sage" | "sky" | "muted";

type Density = "sm" | "md";

type Props = {
  year: number;
  /** 1-indexed month, matching design */
  month: number;
  selected?: number;
  marks?: Record<number, DayMark | DayMark[]>;
  density?: Density;
  onSelectDay?: (day: number) => void;
};

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"] as const;

const MARK_COLOR: Record<DayMark, string> = {
  indigo: colors.indigo,
  sage: "#7fa085",
  sky: "#6e90b3",
  muted: colors.muted2,
};

function dayTextColor(isSelected: boolean, dow: number): string {
  if (isSelected) return colors.cream;
  if (dow === 0) return colors.indigo;
  return colors.ink2;
}

function toMarkList(value: DayMark | DayMark[] | undefined): DayMark[] {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  return [value];
}

export function MiniMonthCalendar({
  year,
  month,
  selected,
  marks = {},
  density = "md",
  onSelectDay,
}: Props) {
  const firstDow = new Date(year, month - 1, 1).getDay();
  const daysInMonth = new Date(year, month, 0).getDate();

  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const cellHeight = density === "sm" ? 36 : 44;
  const fontSize = density === "sm" ? 13 : 14;

  return (
    <View style={styles.root}>
      <View style={styles.dowRow}>
        {WEEKDAYS.map((label, i) => (
          <View key={label} style={styles.dowCell}>
            <Text
              style={[
                styles.dowText,
                { color: i === 0 ? colors.indigo : colors.muted },
              ]}
            >
              {label}
            </Text>
          </View>
        ))}
      </View>

      <View style={styles.grid}>
        {cells.map((day, i) => {
          if (day === null) {
            return <View key={i} style={[styles.cell, { height: cellHeight }]} />;
          }
          const isSelected = day === selected;
          const dow = (firstDow + day - 1) % 7;
          const markList = toMarkList(marks[day]);

          return (
            <Pressable
              key={i}
              onPress={onSelectDay ? () => onSelectDay(day) : undefined}
              style={[styles.cell, { height: cellHeight }]}
            >
              <View
                style={[
                  styles.dayDisc,
                  isSelected && { backgroundColor: colors.ink },
                ]}
              >
                <Text
                  style={[
                    styles.dayText,
                    {
                      fontSize,
                      color: dayTextColor(isSelected, dow),
                      fontWeight: isSelected ? "600" : "500",
                    },
                  ]}
                >
                  {day}
                </Text>
              </View>
              {markList.length > 0 ? (
                <View style={styles.markRow}>
                  {markList.slice(0, 3).map((m, k) => (
                    <View
                      key={k}
                      style={[styles.markDot, { backgroundColor: MARK_COLOR[m] }]}
                    />
                  ))}
                </View>
              ) : null}
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}
