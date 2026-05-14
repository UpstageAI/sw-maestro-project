import type { TravelDuration } from '../../types';

const DURATIONS: { value: TravelDuration; label: string; emoji: string }[] = [
  { value: '당일', label: '당일치기', emoji: '☀️' },
  { value: '1박 2일', label: '1박 2일', emoji: '🌙' },
  { value: '2박 3일', label: '2박 3일', emoji: '✨' },
];

interface DurationSelectProps {
  value: TravelDuration | '';
  onChange: (value: TravelDuration) => void;
}

export default function DurationSelect({ value, onChange }: DurationSelectProps) {
  return (
    <fieldset>
      <legend className="block text-sm font-semibold text-gray-700 mb-2">
        여행 기간 <span className="text-red-400" aria-label="필수">*</span>
      </legend>
      <div className="grid grid-cols-3 gap-2">
        {DURATIONS.map(({ value: dv, label, emoji }) => (
          <label
            key={dv}
            className={[
              'flex flex-col items-center gap-1.5 py-3 px-2 rounded-xl border cursor-pointer transition-all text-center',
              value === dv
                ? 'border-primary bg-cream-dark text-primary'
                : 'border-gray-200 bg-white text-gray-700 hover:border-primary-light',
            ].join(' ')}
          >
            <input
              type="radio"
              name="travelDuration"
              value={dv}
              checked={value === dv}
              onChange={() => onChange(dv)}
              className="sr-only"
            />
            <span className="text-xl" aria-hidden="true">{emoji}</span>
            <span className="text-sm font-medium">{label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
