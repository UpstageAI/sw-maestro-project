import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { CalendarDays, Home } from "lucide-react-native";

import { colors } from "../constants/theme";
import { CalendarScreen } from "../screens/CalendarScreen";
import { EventDetailScreen } from "../screens/EventDetailScreen";
import { HomeScreen } from "../screens/HomeScreen";
import { ScheduleFlowScreen } from "../screens/ScheduleFlowScreen";
import type { MainTabParamList, RootStackParamList } from "./types";

const RootStack = createNativeStackNavigator<RootStackParamList>();
const MainTabs = createBottomTabNavigator<MainTabParamList>();

function MainTabsNavigator() {
  return (
    <MainTabs.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.indigo,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: {
          backgroundColor: colors.paper,
          borderTopColor: colors.line,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: "800",
        },
      }}
    >
      <MainTabs.Screen
        name="Home"
        component={HomeScreen}
        options={{
          title: "홈",
          tabBarIcon: ({ color, size }) => (
            <Home color={color} size={size} strokeWidth={2.4} />
          ),
        }}
      />
      <MainTabs.Screen
        name="Calendar"
        component={CalendarScreen}
        options={{
          title: "캘린더",
          tabBarIcon: ({ color, size }) => (
            <CalendarDays color={color} size={size} strokeWidth={2.4} />
          ),
        }}
      />
    </MainTabs.Navigator>
  );
}

export function RootNavigator() {
  return (
    <RootStack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.cream },
      }}
    >
      <RootStack.Screen name="MainTabs" component={MainTabsNavigator} />
      <RootStack.Screen name="ScheduleFlow" component={ScheduleFlowScreen} />
      <RootStack.Screen name="EventDetail" component={EventDetailScreen} />
    </RootStack.Navigator>
  );
}
