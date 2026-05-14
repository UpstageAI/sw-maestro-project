export interface AnalysisStep {
  id: number;
  title: string;
  description: string;
  durationMs: number;
}

export const ANALYSIS_FLOW: AnalysisStep[] = [
  {
    id: 1,
    title: '입력값 검증',
    description: '생년월일과 출발지를 살펴보고 있어요.',
    durationMs: 500,
  },
  {
    id: 2,
    title: '사주 분석',
    description: '천간과 지지의 흐름을 천천히 읽어내는 중...',
    durationMs: 700,
  },
  {
    id: 3,
    title: '여행 스타일 매핑',
    description: '오늘의 기운에 어울리는 여행의 결을 찾고 있어요.',
    durationMs: 600,
  },
  {
    id: 4,
    title: '여행지 검색',
    description: '국내 후보지를 하나씩 살펴보고 있습니다.',
    durationMs: 600,
  },
  {
    id: 5,
    title: '추천 점수 계산',
    description: '당신의 조건과 가장 잘 맞는 곳을 고르는 중...',
    durationMs: 500,
  },
  {
    id: 6,
    title: '추천 이유 생성',
    description: '왜 어울리는지 한 줄씩 정리하고 있어요.',
    durationMs: 500,
  },
];