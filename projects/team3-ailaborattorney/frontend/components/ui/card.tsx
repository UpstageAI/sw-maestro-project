import * as React from "react";
export function Card({ className = "", children, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`rounded-2xl bg-white border border-grey-200 ${className}`} {...rest}>
      {children}
    </div>
  );
}
