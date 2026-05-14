import type { RouteProp } from "@react-navigation/native";
import {
  useFocusEffect,
  useNavigation,
  useRoute,
} from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useCallback, useMemo, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { listSchedules } from "../api/schedules";
import {
  type DayMark,
  KIcon,
  MiniMonthCalendar,
} from "../components";
import { colors } from "../constants/theme";
import type {
  MainTabParamList,
  RootStackParamList,
} from "../navigation/types";
import type { Schedule } from "../types/schedule";
import { reminderText } from "../utils/scheduleGuards";
import { styles } from "./CalendarScreen.style";

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<MainTabParamList, "Calendar">;

const WEEKDAYS_LONG = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
] as const;
const WEEKDAYS_SHORT = ["일", "월", "화", "수", "목", "금", "토"] as const;
const MONTH_NAMES_EN = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
] as const;

const ACCENT_BY_MARK: Record<DayMark, string> = {
  indigo: colors.indigo,
  sky: "#6e90b3",
  sage: "#7fa085",
  muted: colors.muted2,
};

function categoryMark(schedule: Schedule): DayMark {
  const t = schedule.title.toLowerCase();
  if (t.includes("회의") || t.includes("미팅")) return "sky";
  if (t.includes("마감") || t.includes("제출")) return "indigo";
  return "sage";
}

function timeOfDay(iso: string): string {
  const d = new Date(iso);
  return `${d.getHours().toString().padStart(2, "0")}:${d
    .getMinutes()
    .toString()
    .padStart(2, "0")}`;
}

export function CalendarScreen() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const insets = useSafeAreaInsets();

  const initial = route.params?.selectedDate
    ? new Date(route.params.selectedDate)
    : new Date();

  const [year, setYear] = useState(initial.getFullYear());
  const [month, setMonth] = useState(initial.getMonth() + 1);
  const [selectedDay, setSelectedDay] = useState(initial.getDate());
  const [schedules, setSchedules] = useState<Schedule[]>([]);

  const freshScheduleId = route.params?.freshScheduleId;

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      void (async () => {
        try {
          const all = await listSchedules();
          if (!cancelled) setSchedules(all);
        } catch {
          if (!cancelled) setSchedules([]);
        }
      })();
      return () => {
        cancelled = true;
      };
    }, []),
  );

  const monthSchedules = useMemo(
    () =>
      schedules.filter((s) => {
        const d = new Date(s.start_at);
        return d.getFullYear() === year && d.getMonth() + 1 === month;
      }),
    [schedules, year, month],
  );

  const marks = useMemo(() => {
    const map: Record<number, DayMark[]> = {};
    for (const s of monthSchedules) {
      const day = new Date(s.start_at).getDate();
      const mark = categoryMark(s);
      const list = map[day] ?? [];
      if (!list.includes(mark)) list.push(mark);
      map[day] = list;
    }
    return map;
  }, [monthSchedules]);

  const selectedDaySchedules = useMemo(
    () =>
      monthSchedules
        .filter((s) => new Date(s.start_at).getDate() === selectedDay)
        .sort(
          (a, b) =>
            new Date(a.start_at).getTime() - new Date(b.start_at).getTime(),
        ),
    [monthSchedules, selectedDay],
  );

  const selectedDate = new Date(year, month - 1, selectedDay);
  const selectedWeekdayLong = WEEKDAYS_LONG[selectedDate.getDay()];
  const selectedWeekdayShort = WEEKDAYS_SHORT[selectedDate.getDay()];
  const showFreshBadge =
    typeof freshScheduleId === "number" &&
    selectedDaySchedules.some((s) => s.id === freshScheduleId);

  const goPrev = () => {
    const d = new Date(year, month - 2, 1);
    setYear(d.getFullYear());
    setMonth(d.getMonth() + 1);
    setSelectedDay(1);
  };
  const goNext = () => {
    const d = new Date(year, month, 1);
    setYear(d.getFullYear());
    setMonth(d.getMonth() + 1);
    setSelectedDay(1);
  };

  const openDetail = (id: number) =>
    navigation.navigate("EventDetail", { scheduleId: id });

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.topBar}>
        <View>
          <Text style={styles.topYear}>{year}</Text>
          <Text style={styles.topMonth}>
            {`${month}월 ${MONTH_NAMES_EN[month - 1]}`}
          </Text>
        </View>
        <View style={styles.topActions}>
          <Pressable style={styles.topActionBtn} onPress={goPrev}>
            <KIcon name="chevron-left" size={16} color={colors.muted} />
          </Pressable>
          <Pressable style={styles.topActionBtn} onPress={goNext}>
            <KIcon name="chevron-right" size={16} color={colors.muted} />
          </Pressable>
          <Pressable
            style={styles.topActionBtn}
            onPress={() =>
              navigation.navigate("ScheduleFlow", { initialText: "" })
            }
          >
            <KIcon name="plus" size={16} color={colors.muted} />
          </Pressable>
        </View>
      </View>

      <View style={styles.calendarWrap}>
        <MiniMonthCalendar
          year={year}
          month={month}
          selected={selectedDay}
          marks={marks}
          onSelectDay={setSelectedDay}
        />
      </View>

      <View style={styles.daySheet}>
        <View style={styles.daySheetHeader}>
          <View>
            <Text style={styles.daySheetSubtitle}>
              {`${selectedWeekdayShort} · ${selectedWeekdayLong}`}
            </Text>
            <Text style={styles.daySheetTitle}>
              {`${month}월 ${selectedDay}일 · 일정 ${selectedDaySchedules.length}`}
            </Text>
          </View>
          {showFreshBadge ? (
            <View style={styles.newBadge}>
              <Text style={styles.newBadgeText}>NEW</Text>
            </View>
          ) : null}
        </View>

        <ScrollView
          contentContainerStyle={styles.daySheetList}
          showsVerticalScrollIndicator={false}
        >
          {selectedDaySchedules.length === 0 ? (
            <Text style={styles.emptyText}>일정 없음</Text>
          ) : (
            selectedDaySchedules.map((s) => (
              <DayItemRow
                key={s.id}
                schedule={s}
                highlight={freshScheduleId === s.id}
                onPress={() => openDetail(s.id)}
              />
            ))
          )}
        </ScrollView>
      </View>
    </View>
  );
}

type DayItemRowProps = {
  schedule: Schedule;
  highlight: boolean;
  onPress: () => void;
};

function DayItemRow({ schedule, highlight, onPress }: DayItemRowProps) {
  const accent = ACCENT_BY_MARK[categoryMark(schedule)];
  const bg = highlight ? colors.indigo50 : colors.cream;
  const border = highlight ? colors.indigo100 : "transparent";

  return (
    <Pressable
      onPress={onPress}
      style={[
        styles.dayItem,
        { backgroundColor: bg, borderColor: border },
      ]}
    >
      <View style={[styles.dayItemBar, { backgroundColor: accent }]} />
      <Text style={styles.dayItemTime}>{timeOfDay(schedule.start_at)}</Text>
      <View style={{ flex: 1 }}>
        <Text style={styles.dayItemTitle}>{schedule.title}</Text>
        <View style={styles.dayItemMetaRow}>
          {schedule.location ? (
            <Text style={styles.dayItemMeta}>{schedule.location}</Text>
          ) : null}
          {schedule.reminder_minutes !== null ? (
            <Text style={styles.dayItemAlarm}>
              ● {reminderText(schedule.reminder_minutes)}
            </Text>
          ) : null}
        </View>
      </View>
    </Pressable>
  );
}
