import type { TravelStyleDef } from '../../mocks/travelStyles';

interface StyleBadgeProps {
  style: TravelStyleDef;
  size?: 'sm' | 'md';
}

export default function StyleBadge({ style, size = 'md' }: StyleBadgeProps) {
  const isLg = size === 'md';
  return (
    <div
      className={[
        'inline-flex items-center gap-2 rounded-full border-2 bg-white shadow-soft',
        isLg ? 'pl-2.5 pr-4 py-1.5' : 'pl-2 pr-3 py-1',
      ].join(' ')}
      style={{ borderColor: style.color }}
    >
      <span
        className={[
          'flex items-center justify-center rounded-full text-white',
          isLg ? 'w-7 h-7 text-base' : 'w-5 h-5 text-xs',
        ].join(' ')}
        style={{ backgroundColor: style.color }}
        aria-hidden="true"
      >
        {style.emoji}
      </span>
      <span
        className={['font-bold tracking-tight', isLg ? 'text-sm' : 'text-xs'].join(' ')}
        style={{ color: style.color }}
      >
        {style.label}
      </span>
    </div>
  );
}
