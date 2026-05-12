import type { BirthHour } from '../../types';

const BIRTH_HOURS: BirthHour[] = [
  '모름',
  '자시(23-01)',
  '축시(01-03)',
  '인시(03-05)',
  '묘시(05-07)',
  '진시(07-09)',
  '사시(09-11)',
  '오시(11-13)',
  '미시(13-15)',
  '신시(15-17)',
  '유시(17-19)',
  '술시(19-21)',
  '해시(21-23)',
];

interface DateTimeInputProps {
  birthDate: string;
  birthHour: BirthHour;
  onBirthDateChange: (value: string) => void;
  onBirthHourChange: (value: BirthHour) => void;
}

export default function DateTimeInput({
  birthDate,
  birthHour,
  onBirthDateChange,
  onBirthHourChange,
}: DateTimeInputProps) {
  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="space-y-4">
      <div>
        <label
          htmlFor="birthDate"
          className="block text-sm font-semibold text-gray-700 mb-1.5"
        >
          생년월일 <span className="text-red-400" aria-label="필수">*</span>
        </label>
        <input
          type="date"
          id="birthDate"
          value={birthDate}
          max={today}
          onChange={(e) => onBirthDateChange(e.target.value)}
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-gray-900 text-base
            focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
            bg-white transition-all"
          required
          aria-required="true"
        />
      </div>

      <div>
        <label
          htmlFor="birthHour"
          className="block text-sm font-semibold text-gray-700 mb-1.5"
        >
          출생시간 <span className="text-gray-400 font-normal text-xs">(선택)</span>
        </label>
        <select
          id="birthHour"
          value={birthHour}
          onChange={(e) => onBirthHourChange(e.target.value as BirthHour)}
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-gray-900 text-base
            focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
            bg-white transition-all appearance-none"
          aria-label="출생시간 선택"
        >
          {BIRTH_HOURS.map((hour) => (
            <option key={hour} value={hour}>
              {hour === '모름' ? '모름 (선택 안 함)' : hour}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
