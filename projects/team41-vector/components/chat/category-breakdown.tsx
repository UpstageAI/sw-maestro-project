'use client';

// ─── CategoryBreakdown ───
// CSV 업로드 직후 1회만 보여주는 카테고리별 지출 가로 바 차트.
// 가장 많이 쓴 카테고리가 꽉 찬 바 = 100%가 되고,
// 나머지는 그 비율에 맞게 줄어드는 상대 스케일을 사용한다.

type Props = {
  data: Record<string, number>; // { 카테고리명: 금액 }
};

export function CategoryBreakdown({ data }: Props) {
  // 금액 내림차순으로 정렬
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);

  // 가장 큰 값 = 바 100% 기준
  const max = Math.max(entries[0]?.[1] ?? 1, 1);

  return (
    <div className="my-2 space-y-2 rounded-xl bg-white/60 p-4">
      <p className="mb-2 text-xs font-semibold text-gray-500">카테고리별 지출</p>
      {entries.map(([category, amount]) => (
        <div key={category} className="flex items-center gap-2">
          {/* 카테고리 이름: 오른쪽 정렬, 고정 너비 */}
          <span className="w-16 shrink-0 text-right text-xs text-gray-600">
            {category}
          </span>

          {/* 보라 그라데이션 바: 최대값 대비 비율로 너비 결정 */}
          <div className="flex-1">
            <div
              className="h-5 rounded"
              style={{
                width: `${(amount / max) * 100}%`,
                background: 'linear-gradient(90deg, #8b5cf6, #5b21b6)',
                minWidth: 4, // 금액이 매우 작아도 바가 보이도록
              }}
            />
          </div>

          {/* 금액: 오른쪽 정렬, 고정 너비 */}
          <span className="w-20 shrink-0 text-right text-xs text-gray-500">
            {amount.toLocaleString()}원
          </span>
        </div>
      ))}
    </div>
  );
}
