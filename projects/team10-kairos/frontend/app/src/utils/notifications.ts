import * as Notifications from "expo-notifications";

import type { Schedule } from "../types/schedule";

export type NotificationScheduleResult =
  | "scheduled"
  | "permission-denied"
  | "skipped-past"
  | "failed";

export async function scheduleLocalNotification(
  schedule: Schedule,
): Promise<NotificationScheduleResult> {
  const reminderMinutes = schedule.reminder_minutes ?? 30;
  const triggerAt = new Date(
    new Date(schedule.start_at).getTime() - reminderMinutes * 60 * 1000,
  );

  if (triggerAt.getTime() <= Date.now()) {
    return "skipped-past";
  }

  try {
    const existing = await Notifications.getPermissionsAsync();
    const permission =
      existing.status === "granted"
        ? existing
        : await Notifications.requestPermissionsAsync();

    if (permission.status !== "granted") {
      return "permission-denied";
    }

    await Notifications.scheduleNotificationAsync({
      content: {
        title: "Kairos 일정 알림",
        body: `${schedule.title} 일정이 곧 시작돼요.`,
        data: { scheduleId: schedule.id },
      },
      trigger: triggerAt as unknown as Notifications.NotificationTriggerInput,
    });
    return "scheduled";
  } catch (error) {
    console.warn("[kairos:notification] scheduling failed", error);
    return "failed";
  }
}

export function notificationMessage(
  result: NotificationScheduleResult,
): string {
  switch (result) {
    case "scheduled":
      return "일정과 알림이 예약됐어요.";
    case "permission-denied":
      return "일정은 저장됐지만 알림 권한이 꺼져 있어요.";
    case "skipped-past":
      return "일정은 저장됐어요. 알림 시간이 지나 알림은 예약하지 않았어요.";
    case "failed":
      return "일정은 저장됐지만 알림 예약에 실패했어요.";
  }
}
