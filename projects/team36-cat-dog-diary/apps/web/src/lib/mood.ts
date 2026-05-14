import type { MoodTag } from "@cat-dog-diary/shared-types";

export const MOOD_COLOR_VAR: Record<MoodTag, string> = {
  행복: "var(--mood-happy)",
  신남: "var(--mood-excited)",
  평온: "var(--mood-calm)",
  졸림: "var(--mood-sleepy)",
  심심: "var(--mood-bored)",
  슬픔: "var(--mood-sad)",
  까칠: "var(--mood-grumpy)",
};
