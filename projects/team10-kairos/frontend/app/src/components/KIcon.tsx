import {
  AlertTriangle,
  ArrowUp,
  Bell,
  Calendar,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  Home,
  type LucideProps,
  MapPin,
  Menu,
  Pencil,
  Plus,
  Search,
  Send,
  Sparkles,
  User,
  Volume2,
  X,
} from "lucide-react-native";
import type { ComponentType } from "react";

import { colors } from "../constants/theme";

export type KIconName =
  | "spark"
  | "send"
  | "arrow-up"
  | "calendar"
  | "clock"
  | "pin"
  | "bell"
  | "check"
  | "x"
  | "edit"
  | "plus"
  | "home"
  | "list"
  | "user"
  | "warn"
  | "chevron-left"
  | "chevron-right"
  | "chevron-down"
  | "search"
  | "sparkle-fill"
  | "sound";

const ICONS: Record<KIconName, ComponentType<LucideProps>> = {
  spark: Sparkles,
  send: Send,
  "arrow-up": ArrowUp,
  calendar: Calendar,
  clock: Clock,
  pin: MapPin,
  bell: Bell,
  check: Check,
  x: X,
  edit: Pencil,
  plus: Plus,
  home: Home,
  list: Menu,
  user: User,
  warn: AlertTriangle,
  "chevron-left": ChevronLeft,
  "chevron-right": ChevronRight,
  "chevron-down": ChevronDown,
  search: Search,
  "sparkle-fill": Sparkles,
  sound: Volume2,
};

type Props = {
  name: KIconName;
  size?: number;
  color?: string;
  strokeWidth?: number;
  fill?: string;
};

export function KIcon({
  name,
  size = 20,
  color = colors.ink,
  strokeWidth = 1.6,
  fill,
}: Props) {
  const Icon = ICONS[name];
  const isFilled = name === "sparkle-fill";
  return (
    <Icon
      size={size}
      color={color}
      strokeWidth={strokeWidth}
      fill={fill ?? (isFilled ? color : "none")}
    />
  );
}
