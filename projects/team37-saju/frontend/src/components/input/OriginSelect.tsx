import type { DepartureRegion } from '../../types';

const REGIONS: DepartureRegion[] = [
  '서울',
  '경기',
  '부산',
  '대구',
  '광주',
  '대전',
  '기타',
];

interface OriginSelectProps {
  value: DepartureRegion | '';
  onChange: (value: DepartureRegion) => void;
}

export default function OriginSelect({ value, onChange }: OriginSelectProps) {
  return (
    <div>
      <label
        htmlFor="departure"
        className="block text-sm font-semibold text-gray-700 mb-1.5"
      >
        출발지 <span className="text-red-400" aria-label="필수">*</span>
      </label>
      <select
        id="departure"
        value={value}
        onChange={(e) => onChange(e.target.value as DepartureRegion)}
        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-gray-900 text-base
          focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
          bg-white transition-all appearance-none"
        required
        aria-required="true"
      >
        <option value="" disabled>
          출발 지역을 선택하세요
        </option>
        {REGIONS.map((region) => (
          <option key={region} value={region}>
            {region}
          </option>
        ))}
      </select>
    </div>
  );
}
