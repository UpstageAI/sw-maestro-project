import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useEffect, useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { listSchedules } from "../api/schedules";
import { Chip, KIcon, KLogo } from "../components";
import { colors, shadow } from "../constants/theme";
import type { RootStackParamList } from "../navigation/types";
import type { Schedule } from "../types/schedule";
import { formatTime, toDateKey, todayKey } from "../utils/dates";
import { reminderText } from "../utils/scheduleGuards";
import { styles } from "./HomeScreen.style";

type Nav = NativeStackNavigationProp<RootStackParamList>;

const SUGGESTIONS = [
  "내일 오후 3시 병원 예약",
  "금요일 자정까지 과제 제출",
  "다음 주 월 10시 회의",
];

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"] as const;

type CategoryStyle = { label: string; bg: string; fg: string };

const CATEGORY_DEFAULT: CategoryStyle = {
  label: "개인",
  bg: colors.sageTint,
  fg: "#5b7a64",
};

function formatTodayHeader(date: Date): string {
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const weekday = WEEKDAYS[date.getDay()];
  const hour = date.getHours();
  const minute = date.getMinutes().toString().padStart(2, "0");
  const period = hour < 12 ? "오전" : "오후";
  const hour12 = hour % 12 === 0 ? 12 : hour % 12;
  return `${month}월 ${day}일 ${weekday}요일 · ${period} ${hour12}:${minute}`;
}

function categoryFor(schedule: Schedule): CategoryStyle {
  const title = schedule.title.toLowerCase();
  if (title.includes("회의") || title.includes("미팅")) {
    return { label: "회의", bg: colors.mist, fg: colors.muted };
  }
  if (title.includes("마감") || title.includes("제출")) {
    return { label: "마감", bg: colors.indigo50, fg: colors.indigo };
  }
  return CATEGORY_DEFAULT;
}

function metaLineFor(schedule: Schedule): string {
  const parts: string[] = [];
  if (schedule.location) parts.push(schedule.location);
  if (schedule.reminder_minutes !== null) {
    parts.push(`🔔 ${reminderText(schedule.reminder_minutes)}`);
  }
  return parts.join(" · ");
}

export function HomeScreen() {
  const navigation = useNavigation<Nav>();
  const insets = useSafeAreaInsets();
  const [text, setText] = useState("");
  const [todays, setTodays] = useState<Schedule[]>([]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const all = await listSchedules();
        if (cancelled) return;
        const key = todayKey();
        const filtered = all
          .filter((s) => toDateKey(s.start_at) === key)
          .sort(
            (a, b) =>
              new Date(a.start_at).getTime() - new Date(b.start_at).getTime(),
          );
        setTodays(filtered);
      } catch {
        if (!cancelled) setTodays([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const submit = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    setText("");
    navigation.navigate("ScheduleFlow", { initialText: trimmed });
  };

  const todayHeader = formatTodayHeader(new Date());

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.topBar}>
          <KLogo size={20} />
          <Pressable style={styles.avatarButton}>
            <KIcon name="user" size={17} color={colors.ink2} />
          </Pressable>
        </View>

        <View style={styles.heroHeader}>
          <Text style={styles.heroSubtitle}>{todayHeader}</Text>
          <Text style={styles.heroTitle}>
            오늘은 무엇을{"\n"}맞춰드릴까요?
          </Text>
        </View>

        <View style={[styles.heroCard, shadow.md]}>
          <View style={styles.heroCardKicker}>
            <KIcon name="sparkle-fill" size={14} color={colors.indigo} />
            <Text style={styles.heroCardKickerText}>
              한 문장으로 일정 등록
            </Text>
          </View>
          <TextInput
            value={text}
            onChangeText={setText}
            placeholder={
              "평소 말하듯 입력해 주세요.\n날짜·시간·장소·알림을 함께 적으면 더 빨라요."
            }
            placeholderTextColor={colors.muted2}
            multiline
            style={styles.heroInput}
            returnKeyType="send"
            blurOnSubmit
            onSubmitEditing={() => submit(text)}
          />
          <View style={styles.heroCardFooter}>
            <View style={styles.heroFooterLeft}>
              <View style={styles.heroFooterCircle}>
                <KIcon name="sound" size={16} color={colors.muted} />
              </View>
              <View style={styles.heroFooterCircle}>
                <KIcon name="plus" size={16} color={colors.muted} />
              </View>
            </View>
            <Pressable
              onPress={() => submit(text)}
              style={({ pressed }) => [
                styles.submitButton,
                { opacity: pressed || !text.trim() ? 0.85 : 1 },
              ]}
            >
              <KIcon
                name="arrow-up"
                size={18}
                color={colors.cream}
                strokeWidth={2.2}
              />
            </Pressable>
          </View>
        </View>

        <View style={styles.suggestionWrap}>
          <Text style={styles.suggestionLabel}>이렇게 말해 보세요</Text>
          <View style={styles.suggestionChips}>
            {SUGGESTIONS.map((s) => (
              <Chip key={s} onPress={() => submit(s)}>
                {s}
              </Chip>
            ))}
          </View>
        </View>

        <View style={styles.todayWrap}>
          <View style={styles.todayHeader}>
            <Text style={styles.todayHeaderLabel}>
              오늘 일정 · {todays.length}
            </Text>
            <Pressable
              onPress={() =>
                navigation.navigate("MainTabs", { screen: "Calendar" })
              }
            >
              <Text style={styles.todayHeaderLink}>전체 보기</Text>
            </Pressable>
          </View>
          {todays.length === 0 ? (
            <Text style={styles.emptyText}>오늘 등록된 일정이 없어요.</Text>
          ) : (
            todays.map((s) => (
              <TodayRow
                key={s.id}
                schedule={s}
                onPress={() =>
                  navigation.navigate("EventDetail", { scheduleId: s.id })
                }
              />
            ))
          )}
        </View>
      </ScrollView>
    </View>
  );
}

type TodayRowProps = {
  schedule: Schedule;
  onPress: () => void;
};

function TodayRow({ schedule, onPress }: TodayRowProps) {
  const tag = categoryFor(schedule);
  const meta = metaLineFor(schedule);
  return (
    <Pressable onPress={onPress} style={styles.todayRow}>
      <Text style={styles.todayRowTime}>
        {formatTime(schedule.start_at).replace(/\s/g, "")}
      </Text>
      <View style={styles.todayRowBody}>
        <Text style={styles.todayRowTitle}>{schedule.title}</Text>
        {meta ? <Text style={styles.todayRowMeta}>{meta}</Text> : null}
      </View>
      <View style={[styles.todayRowTag, { backgroundColor: tag.bg }]}>
        <Text style={[styles.todayRowTagText, { color: tag.fg }]}>
          {tag.label}
        </Text>
      </View>
    </Pressable>
  );
}
