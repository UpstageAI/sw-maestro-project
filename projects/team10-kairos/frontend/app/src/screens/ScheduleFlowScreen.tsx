import type { RouteProp } from "@react-navigation/native";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  AgentBubble,
  AgentTag,
  Chip,
  KButton,
  KIcon,
  ScheduleCard,
  ThinkingDots,
} from "../components";
import { colors } from "../constants/theme";
import type { FlowStatus } from "../features/schedule-flow/model/scheduleFlowModel";
import { useScheduleFlow } from "../features/schedule-flow/model/useScheduleFlow";
import type { RootStackParamList } from "../navigation/types";
import type { ScheduleCandidate } from "../types/schedule";
import { notificationMessage } from "../utils/notifications";
import { reminderText } from "../utils/scheduleGuards";
import { styles } from "./ScheduleFlowScreen.style";

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, "ScheduleFlow">;
type Flow = ReturnType<typeof useScheduleFlow>;

const FAILED_QUICK_CHIPS = [
  "오늘",
  "내일",
  "이번 주 토요일",
  "다음 주 월요일",
];
const NEEDS_INPUT_QUICK_CHIPS = [
  "오전 10시",
  "오후 2시",
  "오후 3시",
  "이번 주 토요일 오후 6시",
];
const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"] as const;

function formatDateLabel(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}월 ${d.getDate()}일 (${WEEKDAYS[d.getDay()]})`;
}

function formatTimeLabel(iso: string): string {
  const d = new Date(iso);
  const h = d.getHours();
  const min = d.getMinutes().toString().padStart(2, "0");
  const period = h < 12 ? "오전" : "오후";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${period} ${h12}:${min}`;
}

function formatTimeRange(startIso: string, endIso: string | null): string {
  const start = formatTimeLabel(startIso);
  if (!endIso) return start;
  const end = formatTimeLabel(endIso);
  return `${start} — ${end.replace(/^오[전후]\s/, "")}`;
}

function placeholderFor(status: FlowStatus): string {
  if (status === "analyzing") return "처리 중…";
  if (status === "needsInput") return "답변 입력";
  if (status === "failed") return "다시 입력하기";
  return "메시지 입력";
}

export function ScheduleFlowScreen() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const insets = useSafeAreaInsets();
  const initialText = route.params?.initialText ?? "";

  const flow = useScheduleFlow({ initialText });
  const [composeText, setComposeText] = useState("");

  const status = flow.status;
  const isInputDisabled =
    status === "analyzing" || status === "saving" || status === "done";

  const handleSubmitInput = () => {
    const trimmed = composeText.trim();
    if (!trimmed) return;
    setComposeText("");
    if (status === "needsInput") {
      flow.submitAnswer(trimmed);
      return;
    }
    flow.setInputText(trimmed);
    void flow.analyze(trimmed);
  };

  const goCalendar = () => {
    if (!flow.savedSchedule) {
      navigation.goBack();
      return;
    }
    navigation.reset({
      index: 0,
      routes: [
        {
          name: "MainTabs",
          params: {
            screen: "Calendar",
            params: { freshScheduleId: flow.savedSchedule.id },
          },
        },
      ],
    });
  };

  const close = () => {
    if (navigation.canGoBack()) navigation.goBack();
  };

  if (status === "done" && flow.savedSchedule) {
    return (
      <DoneView
        scheduleTitle={flow.savedSchedule.title}
        date={formatDateLabel(flow.savedSchedule.start_at)}
        time={formatTimeLabel(flow.savedSchedule.start_at)}
        place={flow.savedSchedule.location ?? undefined}
        alarm={
          flow.notificationResult
            ? notificationMessage(flow.notificationResult)
            : reminderText(flow.savedSchedule.reminder_minutes)
        }
        onPrimary={goCalendar}
        onSecondary={() => {
          flow.resetForAnother();
          navigation.goBack();
        }}
        topInset={insets.top}
      />
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={styles.root}
    >
      <View style={[styles.topBar, { paddingTop: insets.top + 12 }]}>
        <View>
          <Text style={styles.topBarSubtitle}>대화</Text>
          <Text style={styles.topBarTitle}>일정 만들기</Text>
        </View>
        <Pressable style={styles.closeButton} onPress={close}>
          <KIcon name="x" size={16} color={colors.ink} />
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={styles.conversation}
        keyboardShouldPersistTaps="handled"
      >
        {flow.originalText ? (
          <AgentBubble tone="user">{flow.originalText}</AgentBubble>
        ) : null}

        <ConversationBody flow={flow} onClose={close} />
      </ScrollView>

      <InputBar
        topInset={insets.bottom + 14}
        value={composeText}
        onChangeText={setComposeText}
        disabled={isInputDisabled}
        placeholder={placeholderFor(status)}
        onSubmit={handleSubmitInput}
      />
    </KeyboardAvoidingView>
  );
}

type ConversationBodyProps = {
  flow: Flow;
  onClose: () => void;
};

function ConversationBody({ flow, onClose }: ConversationBodyProps) {
  const status = flow.status;
  if (status === "analyzing") return <AnalyzingBody />;
  if (status === "needsInput") {
    return <NeedsInputBody flow={flow} />;
  }
  if (status === "confirming" || status === "saving") {
    return <ConfirmBody flow={flow} onClose={onClose} />;
  }
  if (status === "failed") {
    return <FailedBody flow={flow} />;
  }
  return null;
}

function AnalyzingBody() {
  return (
    <>
      <AgentTag status="입력 분석 중" />
      <View style={styles.thinkingBubble}>
        <ThinkingDots />
      </View>
    </>
  );
}

function NeedsInputBody({ flow }: { flow: Flow }) {
  const subtext = flow.candidate.start_at
    ? "일정 이름을 어떻게 적을까요?"
    : "몇 월 며칠, 몇 시 일정인가요?";
  return (
    <>
      <AgentTag />
      <AgentBubble>
        <Text style={styles.bubbleText}>
          내용을 조금만 더 알려주세요.{"\n"}
          <Text style={styles.bubbleSubtext}>{subtext}</Text>
        </Text>
      </AgentBubble>
      <View style={styles.quickChips}>
        {NEEDS_INPUT_QUICK_CHIPS.map((c) => (
          <Chip key={c} onPress={() => flow.submitAnswer(c)}>
            {c}
          </Chip>
        ))}
      </View>
    </>
  );
}

type ConfirmBodyProps = {
  flow: Flow;
  onClose: () => void;
};

function ConfirmBody({ flow, onClose }: ConfirmBodyProps) {
  const candidate = flow.candidate as ScheduleCandidate & {
    title: string;
    start_at: string;
  };
  if (!candidate.title || !candidate.start_at) return null;
  const isSaving = flow.status === "saving";
  const alarm =
    candidate.reminder_minutes !== null
      ? reminderText(candidate.reminder_minutes)
      : `기본 · ${reminderText(30)}`;
  return (
    <>
      <AgentTag />
      <AgentBubble>아래 내용으로 등록할까요?</AgentBubble>
      <View style={styles.confirmCardWrap}>
        <ScheduleCard
          title={candidate.title}
          date={formatDateLabel(candidate.start_at)}
          time={formatTimeRange(candidate.start_at, candidate.end_at)}
          place={candidate.location ?? undefined}
          alarm={alarm}
        />
      </View>
      <View style={styles.confirmActions}>
        <KButton
          variant="ghost"
          size="md"
          icon="edit"
          full
          style={{ flex: 1 }}
          onPress={onClose}
          disabled={isSaving}
        >
          수정
        </KButton>
        <KButton
          variant="primary"
          size="md"
          icon="check"
          full
          style={{ flex: 1 }}
          onPress={() => void flow.save()}
          disabled={!flow.canConfirm || isSaving}
        >
          {isSaving ? "저장 중…" : "등록하기"}
        </KButton>
      </View>
      <Text style={styles.confirmNote}>
        확인 전까지는 캘린더에 저장되지 않아요
      </Text>
    </>
  );
}

function FailedBody({ flow }: { flow: Flow }) {
  return (
    <>
      <AgentTag status="확인 필요" />
      <View style={styles.failCard}>
        <View style={styles.failHeader}>
          <KIcon name="warn" size={16} color={colors.indigo} />
          <Text style={styles.failHeaderText}>입력을 해석하기 어려워요</Text>
        </View>
        <Text style={styles.failBody}>
          {flow.error ??
            "조금 더 자세한 일정 내용을 알려주세요. 추측해서 등록하지 않을게요."}
        </Text>
        <View style={styles.failChips}>
          {FAILED_QUICK_CHIPS.map((c) => (
            <Chip key={c} onPress={() => flow.submitAnswer(c)}>
              {c}
            </Chip>
          ))}
        </View>
      </View>
      <AgentBubble tone="system" small>
        <Text style={styles.systemText}>
          입력을 다시 다듬거나, 위에서 옵션을 골라주세요.
        </Text>
      </AgentBubble>
    </>
  );
}

type InputBarProps = {
  topInset: number;
  value: string;
  onChangeText: (v: string) => void;
  disabled: boolean;
  placeholder: string;
  onSubmit: () => void;
};

function InputBar({
  topInset,
  value,
  onChangeText,
  disabled,
  placeholder,
  onSubmit,
}: InputBarProps) {
  const empty = !value.trim();
  const blocked = disabled || empty;
  const barBg = disabled ? colors.cream2 : colors.paper;
  const submitBg = blocked ? colors.mist : colors.ink;
  const submitColor = blocked ? colors.muted2 : colors.cream;
  return (
    <View style={[styles.inputBarWrap, { paddingBottom: topInset }]}>
      <View style={[styles.inputBar, { backgroundColor: barBg }]}>
        <KIcon name="plus" size={20} color={colors.muted2} />
        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={colors.muted2}
          editable={!disabled}
          style={styles.inputText}
          onSubmitEditing={onSubmit}
          returnKeyType="send"
          blurOnSubmit
        />
        <Pressable
          disabled={blocked}
          onPress={onSubmit}
          style={({ pressed }) => [
            styles.inputSubmit,
            { backgroundColor: submitBg, opacity: pressed ? 0.85 : 1 },
          ]}
        >
          <KIcon
            name="arrow-up"
            size={14}
            color={submitColor}
            strokeWidth={2.4}
          />
        </Pressable>
      </View>
    </View>
  );
}

type DoneViewProps = {
  scheduleTitle: string;
  date: string;
  time: string;
  place?: string;
  alarm: string;
  onPrimary: () => void;
  onSecondary: () => void;
  topInset: number;
};

function DoneView({
  scheduleTitle,
  date,
  time,
  place,
  alarm,
  onPrimary,
  onSecondary,
  topInset,
}: DoneViewProps) {
  return (
    <View style={[styles.root, { paddingTop: topInset }]}>
      <View style={styles.doneCenter}>
        <View style={styles.successOrb}>
          <View style={styles.successOrbOuter} />
          <View style={styles.successOrbMid} />
          <View style={styles.successOrbInner}>
            <KIcon
              name="check"
              size={32}
              color="#ffffff"
              strokeWidth={2.5}
            />
          </View>
        </View>
        <View style={{ alignItems: "center" }}>
          <Text style={styles.doneTitle}>등록했어요</Text>
          <Text style={styles.doneSubtitle}>
            {`${date} ${time} 일정과\n알림이 예약됐어요`}
          </Text>
        </View>
        <View style={styles.doneCardWrap}>
          <ScheduleCard
            compact
            title={scheduleTitle}
            date={date}
            time={time}
            place={place}
            alarm={`기본 · ${alarm}`}
          />
        </View>
      </View>
      <View style={styles.doneFooter}>
        <KButton variant="primary" size="lg" full onPress={onPrimary}>
          캘린더에서 보기
        </KButton>
        <KButton variant="ghost" size="md" full onPress={onSecondary}>
          일정 하나 더 만들기
        </KButton>
      </View>
    </View>
  );
}
