import type { Schedule, ScheduleCandidate } from "../src/types/schedule";
import { groupSchedulesByDate, toDateKey } from "../src/utils/dates";
import {
  buildSchedulePayload,
  composeInput,
  getFollowUpQuestion,
  getMissingFields,
  isReadyToConfirm,
  reminderText,
} from "../src/utils/scheduleGuards";

describe("schedule guardrails", () => {
  it("keeps answers tied to the original input", () => {
    expect(composeInput("내일 병원 가는 거 알림 맞춰줘.", "오후 3시")).toBe(
      "내일 병원 가는 거 알림 맞춰줘. 추가 정보: 오후 3시",
    );
  });

  it("asks for date and time when start_at is missing", () => {
    const candidate: ScheduleCandidate = {
      title: "병원",
      start_at: null,
      end_at: null,
      location: null,
      reminder_minutes: null,
    };

    expect(getMissingFields(candidate)).toEqual(["start_at"]);
    expect(getFollowUpQuestion(candidate)).toBe("몇 월 며칠, 몇 시 일정인가요?");
    expect(isReadyToConfirm(candidate)).toBe(false);
  });

  it("builds a guarded create payload only when required fields exist", () => {
    const payload = buildSchedulePayload(
      {
        title: " 친구 만나 ",
        start_at: "2026-05-09T18:00:00+09:00",
        end_at: null,
        location: " 홍대 ",
        reminder_minutes: null,
      },
      "원문",
    );

    expect(payload).toEqual({
      title: "친구 만나",
      start_at: "2026-05-09T18:00:00+09:00",
      end_at: null,
      location: "홍대",
      reminder_minutes: 30,
      original_text: "원문",
    });
  });

  it("formats reminder text", () => {
    expect(reminderText(0)).toBe("시작 시간");
    expect(reminderText(60)).toBe("1시간 전");
    expect(reminderText(null)).toBe("30분 전");
  });
});

describe("date grouping", () => {
  it("groups schedules by Asia/Seoul date key", () => {
    const schedules: Schedule[] = [
      schedule(1, "2026-05-08T23:30:00Z"),
      schedule(2, "2026-05-09T01:00:00+09:00"),
    ];

    expect(toDateKey(schedules[0].start_at)).toBe("2026-05-09");
    expect(groupSchedulesByDate(schedules)["2026-05-09"].map((item) => item.id)).toEqual([
      2,
      1,
    ]);
  });
});

function schedule(id: number, start_at: string): Schedule {
  return {
    id,
    title: `일정 ${id}`,
    start_at,
    end_at: null,
    location: null,
    reminder_minutes: 30,
    status: "confirmed",
  };
}
