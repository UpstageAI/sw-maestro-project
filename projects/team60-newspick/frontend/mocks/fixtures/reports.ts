import type { DailyReport } from "../../lib/api/reports";

export const dailyReports: Record<string, DailyReport> = {
  "2026-05-12": {
    date: "2026-05-12",
    updatedAt: "2026-05-12T09:30:00+09:00",
    briefing: {
      headline: "오늘의 핵심",
      summary: "AI 자동화와 통상 압박, 인구 위기가 동시에 부상한 하루였습니다.",
    },
    timeline: [
      {
        articleId: "article_001",
        category: "테크",
        timeLabel: "오늘 09:20",
        title: "오픈AI·앤트로픽, AI 에이전트 경쟁 본격화... 작업 자동화 시대 가시화",
        sourceCount: 4,
        summary:
          "이메일 작성, 코드 실행, 파일 관리 등 실제 작업을 AI가 직접 처리하는 서비스가 빠르게 확산되고 있어요.",
      },
      {
        articleId: "article_002",
        category: "경제",
        timeLabel: "오늘 08:45",
        title: "미국 관세 인상 여파... 반도체·자동차 수출 기업 부담 가중",
        sourceCount: 3,
      },
      {
        articleId: "article_003",
        category: "이슈",
        timeLabel: "오늘 08:10",
        title: "합계출산율 0.75명 역대 최저... 인구전략기획부 신설 추진",
        sourceCount: 2,
      },
    ],
    flow: [
      {
        category: "테크",
        description: "AI 에이전트 경쟁이 업무 자동화 시장으로 본격 확산",
      },
      {
        category: "경제",
        description: "미국 관세 여파로 반도체·자동차 수출 기업 부담 가중",
      },
      {
        category: "이슈",
        description: "합계출산율 역대 최저, 정부 전담 부처 신설로 대응",
      },
    ],
    keywords: [
      { text: "AI 에이전트", weight: 9 },
      { text: "미국 관세", weight: 7 },
      { text: "오픈AI", weight: 6 },
      { text: "출산율", weight: 5 },
      { text: "자동화", weight: 4 },
      { text: "수출", weight: 3 },
      { text: "저출생", weight: 3 },
      { text: "반도체", weight: 2 },
    ],
  },
};
