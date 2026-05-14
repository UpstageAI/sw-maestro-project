import { cn } from "@/lib/utils";

interface IconProps {
  name: string;
  filled?: boolean;
  className?: string;
  size?: number;
  "aria-hidden"?: boolean;
}

/** Material Symbols Outlined wrapper.
 *  Pass `name` as the symbol identifier (e.g. "auto_awesome", "send", "mic"). */
export function Icon({
  name,
  filled = false,
  className,
  size,
  "aria-hidden": ariaHidden = true,
}: IconProps) {
  return (
    <span
      aria-hidden={ariaHidden}
      className={cn(
        "material-symbols-outlined",
        filled && "icon-filled",
        className,
      )}
      style={size ? { fontSize: `${size}px` } : undefined}
    >
      {name}
    </span>
  );
}
