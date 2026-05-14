import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { analyzeSchedule, createSchedule } from "../../../api/schedules";
import type { Schedule, ScheduleCandidate } from "../../../types/schedule";
import {
  type NotificationScheduleResult,
  scheduleLocalNotification,
} from "../../../utils/notifications";
import {
  buildSchedulePayload,
  composeInput,
  isReadyToConfirm,
} from "../../../utils/scheduleGuards";
import {
  emptyCandidate,
  type FlowStatus,
  newScheduleRunId,
  normalizeCandidate,
} from "./scheduleFlowModel";

type UseScheduleFlowOptions = {
  initialText: string;
};

export function useScheduleFlow({ initialText }: UseScheduleFlowOptions) {
  const [status, setStatus] = useState<FlowStatus>(
    initialText ? "analyzing" : "idle",
  );
  const [originalText, setOriginalText] = useState(initialText);
  const [inputText, setInputText] = useState(initialText);
  const [answer, setAnswer] = useState("");
  const [candidate, setCandidate] =
    useState<ScheduleCandidate>(emptyCandidate);
  const [error, setError] = useState<string | null>(null);
  const [savedSchedule, setSavedSchedule] = useState<Schedule | null>(null);
  const [notificationResult, setNotificationResult] =
    useState<NotificationScheduleResult | null>(null);
  const started = useRef(false);
  const runId = useRef(newScheduleRunId());

  const transition = useCallback(
    (next: FlowStatus, reason?: string) => {
      console.info("[kairos:schedule-flow]", {
        workflowRunId: runId.current,
        originalText,
        from: status,
        to: next,
        reason,
      });
      setStatus(next);
    },
    [originalText, status],
  );

  const analyze = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (trimmed.length < 2) {
        setError("일정으로 등록할 내용을 조금 더 자세히 입력해주세요.");
        transition("failed", "input_guardrail");
        return;
      }

      setError(null);
      transition("analyzing");
      try {
        const response = await analyzeSchedule(trimmed);
        const nextCandidate = normalizeCandidate(response.schedule);
        setCandidate(nextCandidate);
        transition(
          isReadyToConfirm(nextCandidate) ? "confirming" : "needsInput",
          isReadyToConfirm(nextCandidate)
            ? "candidate_ready"
            : "missing_required_fields",
        );
      } catch (err) {
        console.warn("[kairos:schedule-flow] analyze failed", err);
        setError("일정 분석 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.");
        transition("failed", "analyze_error");
      }
    },
    [transition],
  );

  useEffect(() => {
    if (initialText && !started.current) {
      started.current = true;
      void analyze(initialText);
    }
  }, [analyze, initialText]);

  const canConfirm = useMemo(() => isReadyToConfirm(candidate), [candidate]);

  const submitIdle = () => {
    const trimmed = inputText.trim();
    if (!trimmed) {
      return;
    }
    runId.current = newScheduleRunId();
    setOriginalText(trimmed);
    setSavedSchedule(null);
    setNotificationResult(null);
    void analyze(trimmed);
  };

  const submitAnswer = (value = answer) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    const composed = composeInput(originalText, trimmed);
    setInputText(composed);
    setAnswer("");
    void analyze(composed);
  };

  const save = async () => {
    if (status !== "confirming" || !canConfirm) {
      return;
    }

    transition("saving", "user_confirmed");
    try {
      const payload = buildSchedulePayload(candidate, originalText);
      const schedule = await createSchedule(payload);
      setSavedSchedule(schedule);
      const notification = await scheduleLocalNotification(schedule);
      setNotificationResult(notification);
      transition("done", "saved");
    } catch (err) {
      console.warn("[kairos:schedule-flow] save failed", err);
      setError("일정을 저장하지 못했어요. 네트워크 상태를 확인하고 다시 시도해주세요.");
      transition("failed", "save_error");
    }
  };

  const resetForAnother = () => {
    runId.current = newScheduleRunId();
    setOriginalText("");
    setInputText("");
    setCandidate(emptyCandidate);
    setSavedSchedule(null);
    setNotificationResult(null);
    transition("idle", "create_another");
  };

  return {
    answer,
    analyze,
    canConfirm,
    candidate,
    error,
    inputText,
    notificationResult,
    originalText,
    resetForAnother,
    save,
    savedSchedule,
    setAnswer,
    setCandidate,
    setInputText,
    status,
    submitAnswer,
    submitIdle,
  };
}
