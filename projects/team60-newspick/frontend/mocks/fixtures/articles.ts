import type { ArticleSummary } from "../../lib/api/feed";
import type { ArticleDetail } from "../../lib/api/articles";

export const feedArticles: ArticleSummary[] = [
  {
    id: "article_001",
    title: "오픈AI·앤트로픽, AI 에이전트 경쟁 본격화... 작업 자동화 시대 가시화",
    source: "ZDNet Korea",
    category: "테크",
    publishedAt: "2026-05-10T09:20:00+09:00",
    summary: [
      "오픈AI와 앤트로픽이 잇따라 에이전트 기능을 공개하며 단순 대화를 넘어 업무 자동화 시장에 진입하고 있어요.",
      "이메일 작성, 코드 실행, 파일 관리 등 실제 작업을 AI가 직접 처리하는 서비스가 빠르게 확산되고 있습니다.",
    ],
    keywords: ["AI 에이전트", "오픈AI", "자동화"],
    status: "summarized",
  },
  {
    id: "article_002",
    title: "미국 관세 인상 여파... 반도체·자동차 수출 기업 비용 부담 가중",
    source: "한국경제",
    category: "경제",
    publishedAt: "2026-05-10T08:45:00+09:00",
    summary: [
      "미국이 주요 교역국에 상호관세를 부과하면서 국내 수출 기업들의 원가 부담이 커지고 있어요.",
      "반도체·자동차·배터리 업종을 중심으로 대응책 마련이 시급하다는 목소리가 나오고 있습니다.",
    ],
    keywords: ["관세", "수출", "무역"],
    status: "summarized",
  },
  {
    id: "article_003",
    title: "합계출산율 0.75명 역대 최저... 정부, 인구전략기획부 신설 추진",
    source: "연합뉴스",
    category: "이슈",
    publishedAt: "2026-05-10T08:10:00+09:00",
    summary: [
      "통계청이 발표한 지난해 합계출산율이 0.75명으로 역대 최저를 기록했어요.",
      "정부는 저출생·고령화 문제를 국가 위기로 규정하고 전담 부처 신설 등 구조적 대응에 나섰습니다.",
    ],
    keywords: ["출산율", "저출생", "인구정책"],
    status: "summarized",
  },
];

export const articleDetails: Record<string, ArticleDetail> = {
  article_001: {
    ...feedArticles[0],
    url: "https://example.com/articles/ai-agent-automation",
    summary: [
      "오픈AI와 앤트로픽이 AI 에이전트 기능을 공개하며 단순 대화를 넘어 실제 업무 처리로 영역을 넓히고 있어요.",
      "이메일 작성, 코드 실행, 웹 탐색 등 사용자 대신 작업을 수행하는 자율 에이전트 서비스가 빠르게 확산되고 있습니다.",
      "국내 IT 기업들도 에이전트 연동 서비스 개발에 속도를 내며 시장 선점 경쟁에 뛰어들고 있어요.",
    ],
    content:
      "오픈AI와 앤트로픽이 AI 에이전트 기능을 공개하며 단순 대화를 넘어 실제 업무 처리로 영역을 넓히고 있어요.\n\n이메일 작성, 코드 실행, 웹 탐색 등 사용자 대신 작업을 수행하는 자율 에이전트 서비스가 빠르게 확산되고 있습니다.\n\n국내 IT 기업들도 에이전트 연동 서비스 개발에 속도를 내며 시장 선점 경쟁에 뛰어들고 있어요.",
    rawText:
      "오픈AI와 앤트로픽이 AI 에이전트 기능을 공개하며 단순 대화를 넘어 실제 업무 처리로 영역을 넓히고 있어요.\n\n이메일 작성, 코드 실행, 웹 탐색 등 사용자 대신 작업을 수행하는 자율 에이전트 서비스가 빠르게 확산되고 있습니다.\n\n국내 IT 기업들도 에이전트 연동 서비스 개발에 속도를 내며 시장 선점 경쟁에 뛰어들고 있어요.",
    rawTextStatus: "full_text",
    importance:
      "AI 에이전트가 실제 업무 도구로 자리 잡으면 기업의 반복 업무 처리 방식과 관련 직무 수요가 빠르게 달라질 수 있어요.",
    context: "AI 에이전트는 사용자의 지시를 받아 여러 앱과 도구를 이어서 실행하는 자동화 기능이에요.",
    contextItems: [
      {
        label: "배경",
        text: "AI 에이전트는 사용자의 지시를 받아 여러 앱과 도구를 이어서 실행하는 자동화 기능이에요.",
      },
      {
        label: "영향",
        text: "이 기능이 확산되면 이메일 작성, 코드 실행, 파일 관리처럼 반복되는 사무 작업이 먼저 바뀔 가능성이 커요.",
      },
    ],
    quiz: [
      {
        id: "q1",
        question: "오픈AI와 앤트로픽의 에이전트 기능 공개는 단순 챗봇 경쟁을 업무 자동화 경쟁으로 넓히는 변화다.",
        answer: true,
        correctTitle: "맞았어요",
        wrongTitle: "조금 달라요",
        explanation: "기사에서 두 회사가 에이전트 기능을 공개하며 반복 업무 자동화 시장으로 경쟁을 넓히고 있다고 설명했어요.",
      },
    ],
    importanceScore: 8,
  },
};
