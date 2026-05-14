import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTravelStore } from '../store/useTravelStore';
import type { BirthHour, DepartureRegion, TravelDuration, TravelRange, TravelStyle } from '../types';
import { Button, Card, Header, PageLayout } from '../components/common';
import {
  DateTimeInput,
  DurationSelect,
  OriginSelect,
  RangeSelect,
  TagPicker,
} from '../components/input';

interface FormState {
  birthDate: string;
  birthHour: BirthHour;
  departure: DepartureRegion | '';
  travelRange: TravelRange | '';
  travelDuration: TravelDuration | '';
  preferredStyles: TravelStyle[];
}

const INITIAL: FormState = {
  birthDate: '',
  birthHour: '모름',
  departure: '',
  travelRange: '',
  travelDuration: '',
  preferredStyles: [],
};

export default function InputPage() {
  const navigate = useNavigate();
  const setUserInput = useTravelStore((s) => s.setUserInput);
  const [form, setForm] = useState<FormState>(INITIAL);

  const isValid =
    form.birthDate.length > 0 &&
    form.departure !== '' &&
    form.travelRange !== '' &&
    form.travelDuration !== '';

  const handleSubmit = () => {
    if (!isValid) return;
    setUserInput({
      birthDate: form.birthDate,
      birthHour: form.birthHour,
      departure: form.departure as DepartureRegion,
      travelRange: form.travelRange as TravelRange,
      travelDuration: form.travelDuration as TravelDuration,
      preferredStyles: form.preferredStyles,
    });
    navigate('/analyzing');
  };

  return (
    <PageLayout background="cream">
      <Header title="내 여행지 찾기" />

      <div className="flex items-center gap-2 mb-5">
        <div className="flex gap-1.5">
          {[1, 2, 3].map((step) => (
            <div
              key={step}
              className={[
                'h-1.5 rounded-full transition-all',
                step === 1 ? 'w-8 bg-primary' : 'w-4 bg-gray-200',
              ].join(' ')}
              aria-hidden="true"
            />
          ))}
        </div>
        <span className="text-xs text-gray-500 ml-1">1 / 3 — 정보 입력</span>
      </div>

      <div className="flex-1 flex flex-col gap-4 overflow-y-auto pb-6">
        <Card>
          <h2 className="text-sm font-bold text-primary mb-4">사주 정보</h2>
          <DateTimeInput
            birthDate={form.birthDate}
            birthHour={form.birthHour}
            onBirthDateChange={(v) => setForm((f) => ({ ...f, birthDate: v }))}
            onBirthHourChange={(v) => setForm((f) => ({ ...f, birthHour: v }))}
          />
        </Card>

        <Card>
          <h2 className="text-sm font-bold text-primary mb-4">출발 정보</h2>
          <OriginSelect
            value={form.departure}
            onChange={(v) => setForm((f) => ({ ...f, departure: v }))}
          />
        </Card>

        <Card>
          <h2 className="text-sm font-bold text-primary mb-4">여행 조건</h2>
          <div className="space-y-5">
            <RangeSelect
              value={form.travelRange}
              onChange={(v) => setForm((f) => ({ ...f, travelRange: v }))}
            />
            <DurationSelect
              value={form.travelDuration}
              onChange={(v) => setForm((f) => ({ ...f, travelDuration: v }))}
            />
          </div>
        </Card>

        <Card>
          <h2 className="text-sm font-bold text-primary mb-4">선호 스타일</h2>
          <TagPicker
            selected={form.preferredStyles}
            onChange={(v) => setForm((f) => ({ ...f, preferredStyles: v }))}
          />
        </Card>
      </div>

      <div className="pt-2">
        <Button
          variant="primary"
          size="lg"
          fullWidth
          disabled={!isValid}
          onClick={handleSubmit}
        >
          분석 시작하기 ✨
        </Button>
        {!isValid && (
          <p className="mt-2 text-center text-xs text-gray-400">
            생년월일·출발지·이동범위·여행기간을 모두 입력해주세요
          </p>
        )}
      </div>
    </PageLayout>
  );
}
