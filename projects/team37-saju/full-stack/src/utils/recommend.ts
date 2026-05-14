import type { RecommendResult, TravelRange, UserInput } from '../types';
import { DESTINATIONS, type EnrichedDestination } from '../mocks/destinations';
import { TRAVEL_STYLES, type StyleKey } from '../mocks/travelStyles';

/**
 * AnalysisResult — 화면 표시용 확장 결과.
 *
 * 기존 store는 `RecommendResult`를 받지만, 우리 화면에는 추가 필드가 필요해
 * 부분형(extends)으로 확장한다. 런타임에 set/get 시 필드는 그대로 유지되며,
 * ResultPage에서 `as AnalysisResult`로 좁혀 사용한다.
 */
export interface AnalysisResult extends RecommendResult {
  destinations: EnrichedDestination[];
  selectedStyles: StyleKey[];
  styleReason: string;
  reasonsByDestination: Record<string, string>;
}

const RANGE_LIMITS: Record<TravelRange, number> = {
  '2시간 이내': 2,
  '4시간 이내': 4,
  '제한 없음': 99,
};

/**
 * 추천 점수 계산 규칙
 * ─────────────────────────────────────────────
 *  1) travelRange 필터: 출발지 기준 이동시간이 제한 시간 이하인 후보만 살림.
 *     - 단, 필터 결과가 3곳 미만이면 전체 풀에서 다시 고른다(빈 결과 방지).
 *  2) 태그 매칭 점수: userInput.preferredStyles ∩ destination.tags 의 크기 × 2
 *     - 사용자가 직접 고른 결을 가장 강하게 반영.
 *  3) 근접 보너스: 제한 시간 대비 이동시간이 짧을수록 가산점.
 *     - (limit - travelTime) / 10  (최대 약 +0.4)
 *  4) duration 가중치: 여행기간이 짧을수록 단거리 후보에 미세 보너스.
 *     - 당일이면 travelTime ≤ 2시간인 곳에 +0.5
 *  5) 점수 동률 시 사용자가 고른 태그가 더 많이 등장하는 순으로 stable sort.
 *  6) 정렬 후 상위 3곳을 추천.
 *  7) 추천된 3곳의 styles 배열 빈도수를 합산해 가장 많이 나온 1~2개를 styleKey로 채택.
 *  8) styleReason / reasonsByDestination 은 미리 짠 템플릿에 키워드만 끼워 넣음.
 *     (LLM 호출 없음 — 순수 deterministic)
 */
export function getRecommendation(input: UserInput): AnalysisResult {
  const limit = RANGE_LIMITS[input.travelRange];

  // 1) travelRange 필터
  const filtered = DESTINATIONS.filter(
    (d) => d.travelTime[input.departure] <= limit,
  );
  const pool = filtered.length >= 3 ? filtered : DESTINATIONS;

  // 2~4) 점수 계산
  const scored = pool.map((dest) => {
    const overlap = dest.tags.filter((t) =>
      input.preferredStyles.includes(t),
    ).length;

    const travelTime = dest.travelTime[input.departure];
    const proximityBonus = Math.max(0, (limit - travelTime) / 10);
    const dayTripBonus =
      input.travelDuration === '당일' && travelTime <= 2 ? 0.5 : 0;

    return {
      dest,
      score: overlap * 2 + proximityBonus + dayTripBonus,
      overlap,
    };
  });

  // 5) 정렬 — 점수 desc, 동률이면 overlap desc
  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return b.overlap - a.overlap;
  });

  // 6) 상위 3곳
  const top3 = scored.slice(0, 3).map((s) => s.dest);

  // 7) styles 빈도수 집계 → 1~2개 선정
  const styleCount = new Map<StyleKey, number>();
  top3.forEach((d) => {
    d.styles.forEach((s) => {
      styleCount.set(s, (styleCount.get(s) ?? 0) + 1);
    });
  });
  const sortedStyles = Array.from(styleCount.entries()).sort(
    (a, b) => b[1] - a[1],
  );
  const selectedStyles: StyleKey[] = sortedStyles
    .slice(0, 2)
    .map(([k]) => k);
  if (selectedStyles.length === 0) {
    selectedStyles.push('EMOTIONAL_RECOVERY');
  }

  // 8) 템플릿 기반 텍스트 생성
  const primary = TRAVEL_STYLES[selectedStyles[0]];
  const secondary = selectedStyles[1]
    ? TRAVEL_STYLES[selectedStyles[1]]
    : null;

  const styleReason = secondary
    ? `지금의 당신에게는 ${primary.label}과 ${secondary.label}의 흐름이 함께 보여요. ${primary.summary} 동시에 ${secondary.summary}`
    : `지금의 당신에게는 ${primary.label}의 결이 가장 강하게 드러나는 시기예요. ${primary.summary}`;

  const reasonsByDestination: Record<string, string> = {};
  top3.forEach((d) => {
    const matched = d.tags.filter((t) =>
      input.preferredStyles.includes(t),
    );
    const matchedText =
      matched.length > 0
        ? `${matched.slice(0, 2).join(' · ')} 을(를) 좋아하는 당신과 잘 맞는 결의 도시`
        : '오늘의 기운과 자연스럽게 맞물리는 흐름의 도시';
    const firstActivity = d.activities[0];
    reasonsByDestination[d.id] =
      `${matchedText}예요. ${d.description} 잠시 일상에서 한 발짝 떨어져 ${firstActivity}만으로도 충분한 시간이 될 거예요.`;
  });

  const top3Names = top3.map((d) => d.name).join(', ');
  const matchReason = `${primary.label}의 흐름에 맞춰 ${top3Names}을(를) 골랐어요.`;

  return {
    destinations: top3,
    sajuAnalysis: styleReason,
    matchReason,
    selectedStyles,
    styleReason,
    reasonsByDestination,
  };
}
