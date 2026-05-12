import * as React from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "lg";

const variants: Record<Variant, string> = {
  primary:
    "bg-toss-blue text-white hover:bg-toss-blue-hover active:bg-toss-blue-pressed disabled:bg-grey-200 disabled:text-grey-400",
  secondary:
    "bg-grey-100 text-grey-900 hover:bg-grey-200 disabled:bg-grey-100 disabled:text-grey-400",
  ghost:
    "bg-transparent text-grey-700 hover:bg-grey-100 disabled:text-grey-400",
  danger:
    "bg-danger text-white hover:opacity-90 disabled:bg-grey-200 disabled:text-grey-400",
};
const sizes: Record<Size, string> = {
  md: "h-11 px-4 text-[14px]",
  lg: "h-14 px-5 text-[16px]",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  fullWidth?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = "", variant = "primary", size = "md", fullWidth, children, ...props }, ref) => (
    <button
      ref={ref}
      className={`inline-flex items-center justify-center gap-2 rounded-xl font-semibold tracking-tight transition-colors disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${fullWidth ? "w-full" : ""} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
);
Button.displayName = "Button";
