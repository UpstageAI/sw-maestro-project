interface DisclaimerBoxProps {
  message?: string;
}

const DEFAULT_MESSAGE =
  '본 결과는 재미와 참고용입니다. 실제 운세 상담이 아니며, 사주 데이터는 더미로 생성됩니다.';

export default function DisclaimerBox({
  message = DEFAULT_MESSAGE,
}: DisclaimerBoxProps) {
  return (
    <div className="rounded-2xl border border-dashed border-primary-light bg-white/60 p-3.5 flex items-start gap-2">
      <span className="text-base shrink-0" aria-hidden="true">
        ⚠️
      </span>
      <p className="text-xs leading-relaxed text-gray-600">{message}</p>
    </div>
  );
}
