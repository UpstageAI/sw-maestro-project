import type { RouteProp } from "@react-navigation/native";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { listSchedules } from "../api/schedules";
import { KIcon, type KIconName } from "../components";
import { colors } from "../constants/theme";
import type { RootStackParamList } from "../navigation/types";
import type { Schedule } from "../types/schedule";
import { reminderText } from "../utils/scheduleGuards";
import { styles } from "./EventDetailScreen.style";

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, "EventDetail">;

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"] as const;

function formatDateLong(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}월 ${d.getDate()}일 ${WEEKDAYS[d.getDay()]}요일`;
}

function formatTime12(d: Date, omitPeriod = false): string {
  const h = d.getHours();
  const min = d.getMinutes().toString().padStart(2, "0");
  const period = h < 12 ? "오전" : "오후";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return omitPeriod ? `${h12}:${min}` : `${period} ${h12}:${min}`;
}

function formatTimeRange(startIso: string, endIso: string | null): string {
  const start = new Date(startIso);
  const startStr = formatTime12(start);
  if (!endIso) return startStr;
  const end = new Date(endIso);
  return `${startStr} — ${formatTime12(end, true)}`;
}

function durationLabel(
  startIso: string,
  endIso: string | null,
): string | undefined {
  if (!endIso) return undefined;
  const minutes = Math.round(
    (new Date(endIso).getTime() - new Date(startIso).getTime()) / 60000,
  );
  if (minutes <= 0) return undefined;
  if (minutes % 60 === 0) return `${minutes / 60}시간`;
  return `${minutes}분`;
}

function daysFromToday(iso: string): string {
  const a = new Date();
  a.setHours(0, 0, 0, 0);
  const b = new Date(iso);
  b.setHours(0, 0, 0, 0);
  const diff = Math.round((b.getTime() - a.getTime()) / 86400000);
  if (diff === 0) return "오늘";
  if (diff > 0) return `오늘부터 +${diff}일`;
  return `${Math.abs(diff)}일 전`;
}

function alarmTime(startIso: string, reminderMinutes: number): string {
  const trigger = new Date(
    new Date(startIso).getTime() - reminderMinutes * 60000,
  );
  return formatTime12(trigger, true);
}

function useScheduleById(scheduleId: number) {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const all = await listSchedules();
        if (cancelled) return;
        setSchedule(all.find((s) => s.id === scheduleId) ?? null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [scheduleId]);

  return { schedule, loading };
}

export function EventDetailScreen() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const insets = useSafeAreaInsets();
  const { schedule, loading } = useScheduleById(route.params.scheduleId);

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.topBar}>
        <Pressable
          style={styles.topBarButton}
          onPress={() => navigation.goBack()}
        >
          <KIcon name="chevron-left" size={18} color={colors.ink} />
        </Pressable>
        <Text style={styles.topBarTitle}>일정 상세</Text>
        <Pressable style={styles.topBarButton}>
          <KIcon name="edit" size={16} color={colors.ink} />
        </Pressable>
      </View>

      <DetailBody schedule={schedule} loading={loading} />
    </View>
  );
}

type DetailBodyProps = {
  schedule: Schedule | null;
  loading: boolean;
};

function DetailBody({ schedule, loading }: DetailBodyProps) {
  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color={colors.indigo} />
      </View>
    );
  }
  if (!schedule) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyText}>일정을 찾을 수 없어요.</Text>
      </View>
    );
  }
  return <DetailContent schedule={schedule} />;
}

function DetailContent({ schedule }: { schedule: Schedule }) {
  const dateText = formatDateLong(schedule.start_at);
  const timeText = formatTimeRange(schedule.start_at, schedule.end_at);
  const duration = durationLabel(schedule.start_at, schedule.end_at);
  const alarmValue = `${reminderText(schedule.reminder_minutes)} (${alarmTime(
    schedule.start_at,
    schedule.reminder_minutes,
  )})`;
  return (
    <>
      <View style={styles.hero}>
        <View style={styles.kairosBadge}>
          <KIcon name="sparkle-fill" size={11} color="#ffffff" />
          <Text style={styles.kairosBadgeText}>Kairos가 등록</Text>
        </View>
        <Text style={styles.heroTitle}>{schedule.title}</Text>
        <Text style={styles.heroMeta}>{`${dateText} · ${timeText}`}</Text>
      </View>

      <ScrollView style={styles.sheet} contentContainerStyle={styles.sheetContent}>
        <DetailRow
          icon="calendar"
          label="날짜"
          value={dateText}
          sub={daysFromToday(schedule.start_at)}
        />
        <DetailRow icon="clock" label="시간" value={timeText} sub={duration} />
        {schedule.location ? (
          <DetailRow
            icon="pin"
            label="장소"
            value={schedule.location}
            sub="지도 보기"
            linkSub
          />
        ) : null}
        <DetailRow
          icon="bell"
          label="알림"
          value={alarmValue}
          sub="알림 추가"
          linkSub
        />

        {schedule.original_text ? (
          <View style={styles.originalCard}>
            <View style={styles.originalIcon}>
              <KIcon name="sparkle-fill" size={13} color="#ffffff" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.originalLabel}>원래 입력</Text>
              <Text style={styles.originalText}>
                {`"${schedule.original_text}"`}
              </Text>
            </View>
          </View>
        ) : null}
      </ScrollView>
    </>
  );
}

type DetailRowProps = {
  icon: KIconName;
  label: string;
  value: string;
  sub?: string;
  linkSub?: boolean;
};

function DetailRow({ icon, label, value, sub, linkSub }: DetailRowProps) {
  return (
    <View style={styles.row}>
      <View style={styles.rowIcon}>
        <KIcon name={icon} size={17} color={colors.ink2} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.rowLabel}>{label}</Text>
        <Text style={styles.rowValue}>{value}</Text>
      </View>
      {sub ? (
        <Text
          style={[
            styles.rowSub,
            { color: linkSub ? colors.indigo : colors.muted },
          ]}
        >
          {sub}
        </Text>
      ) : null}
    </View>
  );
}
