'use client';

import { useEffect, useState } from 'react';

interface ResultCardProps {
  icon: React.ReactNode;
  title: string;
  items: string[] | null;
  visible: boolean;
}

export default function ResultCard({ icon, title, items, visible }: ResultCardProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (visible) {
      const t = setTimeout(() => setMounted(true), 50);
      return () => clearTimeout(t);
    }

    const t = setTimeout(() => setMounted(false), 0);
    return () => clearTimeout(t);
  }, [visible]);

  if (!visible) return null;

  return (
    <div
      className="border border-[#E6E8EB] rounded-[10px] p-5"
      style={{
        opacity: mounted ? 1 : 0,
        transform: mounted ? 'translateY(0)' : 'translateY(8px)',
        transition: 'opacity 400ms ease-out, transform 400ms ease-out',
      }}
    >
      <div className="flex items-start gap-3 mb-3">
        <div className="w-10 h-10 rounded-full bg-[#EFF6FF] flex items-center justify-center shrink-0 text-[18px]">
          {icon}
        </div>
        <h3 className="text-[17px] font-bold text-[#111827] tracking-[-0.5px] pt-2">
          {title}
        </h3>
      </div>

      {items === null ? (
        <SkeletonLines />
      ) : (
        <ul className="space-y-2 pl-1">
          {items.map((item, i) => (
            <li key={i} className="flex gap-2 text-[15px] text-[#374151] leading-relaxed">
              <span className="text-[#2563EB] shrink-0 mt-0.5">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SkeletonLines() {
  return (
    <div className="space-y-2 pl-1">
      {[80, 65, 90].map((w, i) => (
        <div
          key={i}
          className="h-4 rounded"
          style={{
            width: `${w}%`,
            background: 'linear-gradient(90deg, #F3F4F6 25%, #E5E7EB 50%, #F3F4F6 75%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.5s infinite',
          }}
        />
      ))}
    </div>
  );
}
