import type { TravelRange } from '../../types';

const RANGES: { value: TravelRange; label: string; desc: string }[] = [
  { value: '2시간 이내', label: '2시간 이내', desc: '가까운 근교' },
  { value: '4시간 이내', label: '4시간 이내', desc: '당일치기 가능' },
  { value: '제한 없음', label: '제한 없음', desc: '전국 어디든' },
];

interface RangeSelectProps {
  value: TravelRange | '';
  onChange: (value: TravelRange) => void;
}

export default function RangeSelect({ value, onChange }: RangeSelectProps) {
  return (
    <fieldset>
      <legend className="block text-sm font-semibold text-gray-700 mb-2">
        이동 범위 <span className="text-red-400" aria-label="필수">*</span>
      </legend>
      <div className="space-y-2">
        {RANGES.map(({ value: rv, label, desc }) => (
          <label
            key={rv}
            className={[
              'flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-all',
              value === rv
                ? 'border-primary bg-cream-dark text-primary'
                : 'border-gray-200 bg-white text-gray-700 hover:border-primary-light',
            ].join(' ')}
          >
            <input
              type="radio"
              name="travelRange"
              value={rv}
              checked={value === rv}
              onChange={() => onChange(rv)}
              className="accent-primary w-4 h-4 shrink-0"
            />
            <span className="flex-1">
              <span className="font-medium">{label}</span>
              <span className="ml-2 text-xs text-gray-500">{desc}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
