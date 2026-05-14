import type { ReactNode } from 'react';

interface ReasonBlockProps {
  title?: string;
  children: ReactNode;
}

export default function ReasonBlock({
  title = '이 여행지가 어울리는 이유',
  children,
}: ReasonBlockProps) {
  return (
    <div className="rounded-xl bg-cream-dark/60 border border-cream-dark p-3">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span aria-hidden="true">🔮</span>
        <h4 className="text-xs font-bold text-primary tracking-tight">
          {title}
        </h4>
      </div>
      <p className="text-[13px] leading-relaxed text-gray-700">{children}</p>
    </div>
  );
}
