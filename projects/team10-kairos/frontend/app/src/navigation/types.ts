import type { NavigatorScreenParams } from "@react-navigation/native";

export type MainTabParamList = {
  Home: undefined;
  Calendar: { selectedDate?: string; freshScheduleId?: number } | undefined;
};

export type RootStackParamList = {
  MainTabs: NavigatorScreenParams<MainTabParamList> | undefined;
  ScheduleFlow: { initialText?: string } | undefined;
  EventDetail: { scheduleId: number };
};
