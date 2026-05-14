// ─── 전체 타입 정의 ───
// 이 파일이 프로젝트의 타입 중심이다. 새 타입 추가 시 여기에.

// CSV 1행 = 거래 1건
export type Transaction = {
  date: string;     // 날짜 (YYYY-MM-DD)
  category: string; // 카테고리 (예: "카페", "배달", "쇼핑")
  merchant: string; // 가맹점 이름 (예: "스타벅스 강남R점")
  amount: number;   // 결제 금액 (원 단위)
};

// 채팅 메시지 발신자 역할
export type ChatRole = 'user' | 'ai' | 'system';

// 자산 시뮬레이션 결과
// currentPattern: 지금 소비 패턴 유지 시
// optimizedPattern: 위험 패턴 절약 후 시
export type SimulationResult = {
  currentPattern: {
    monthlySaving: number;                          // 월 저축액
    projections: { year: number; assets: number }[]; // 1/3/5년 뒤 자산
  };
  optimizedPattern: {
    monthlySaving: number;
    projections: { year: number; assets: number }[];
  };
};

// 위험 소비 패턴 1건 (Analyzer가 탐지)
export type RiskPattern = {
  type: 'recurring_excess' | 'impulse' | 'unused_subscription' | 'lifestyle_creep';
  description: string; // 사람이 읽을 수 있는 설명
  amount: number;      // 해당 패턴의 총 금액
  frequency: number;   // 발생 횟수
};

// Analyzer가 반환하는 전체 분석 결과
export type AnalysisResult = {
  totalSpending: number;                                    // 전체 지출 합계
  byCategory: Record<string, { count: number; total: number }>; // 카테고리별 건수·합계
  riskPatterns: RiskPattern[];                              // 탐지된 위험 패턴 목록
  topMerchants: { name: string; count: number; total: number }[]; // 지출 상위 가맹점 5곳
  period: { from: string; to: string };                    // 데이터 기간 (YYYY-MM-DD)
};

// coach() 함수 입력값
export type CoachInput = {
  analysis: AnalysisResult;   // Analyzer 분석 결과
  simulation: SimulationResult; // Simulator 시뮬레이션 결과
  userMessage: string;         // 사용자가 방금 보낸 메시지
  chatHistory: { role: 'user' | 'ai'; content: string }[]; // 이전 대화 (최근 20건)
  userId: string;              // 유저 식별자
};

// coach() 함수 반환값
export type CoachOutput = {
  content: string;                                         // AI가 보낼 텍스트
  mission: { text: string; savingAmount: number } | null;  // 제안 미션 (없으면 null)
  profileUpdated?: boolean;    // update_user_profile 툴 호출 시 true → 시뮬레이션 재계산 필요
  completedMissionId?: string; // complete_mission 툴 호출 시 완료된 미션 id
  dailySpending?: DailySpendingData; // get_daily_spending 툴 호출 시 그래프 데이터
};

// 일별 소비 꺾은선 그래프용 데이터
// points 배열의 각 항목: date + total + 카테고리명(동적 키) = 해당 카테고리 금액
export type DailySpendingPoint = {
  date: string;
  total: number;
  [key: string]: number | string; // 카테고리명 → 금액 (동적 키)
};

export type DailySpendingData = {
  month: string;              // 조회한 달 (YYYY-MM)
  points: DailySpendingPoint[]; // 일별 데이터 배열
  categories: string[];       // 그래프에 그릴 카테고리 목록
};

// 채팅창에 표시되는 메시지 1건
export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: number; // epoch ms
  attachment?: { name: string; size: number };     // 첨부 파일 메타
  simulation?: SimulationResult;                    // 자산 시뮬레이션 차트 (초기 분석 시만)
  mission?: { id: string; text: string; savingAmount: number }; // 미션 카드
  categoryBreakdown?: Record<string, number>;       // 카테고리별 지출 바 차트 (초기 분석 시만)
  completedMissionId?: string;                      // 완료 처리된 미션 id
  dailySpending?: DailySpendingData;               // 일별 소비 꺾은선 그래프
};
