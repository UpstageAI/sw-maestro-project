import { END, START, Annotation, StateGraph } from '@langchain/langgraph';
import { reviewAnalysisReportSchema, type ReviewAnalysisReport } from '$lib/types/review';
import { extractJson } from './llmJson';
import { createUpstageModel } from './upstage';

const MAX_REVIEW_CHARS = 12_000;

const ReviewState = Annotation.Root({
	rawReviews: Annotation<string>,
	reviews: Annotation<string>,
	report: Annotation<ReviewAnalysisReport | undefined>
});

function preprocessReviews(state: typeof ReviewState.State) {
	const reviews = state.rawReviews
		.split('\n')
		.map((line) => line.trim())
		.filter(Boolean)
		.filter((line, index, lines) => lines.indexOf(line) === index)
		.join('\n')
		.slice(0, MAX_REVIEW_CHARS);

	return { reviews };
}

async function analyzeReviews(state: typeof ReviewState.State) {
	const model = createUpstageModel();
	const response = await model.invoke([
		{
			role: 'system',
			content:
				'당신은 배달앱 리뷰 분석 전문가입니다. 음식점 사장님이 바로 실행할 수 있는 운영 개선 인사이트를 제공합니다. 반드시 한국어로 답변하세요. 간결하고 실용적인 보고서 스타일로 작성하세요. 반드시 JSON만 출력하세요.'
		},
		{
			role: 'user',
			content: `아래 배달앱 리뷰를 분석하세요.

출력 형식:
{
  "summary": "전체 리뷰 요약",
  "positives": ["긍정 피드백"],
  "negatives": ["부정 피드백"],
  "recurringIssues": ["반복적으로 나타나는 문제"],
  "suggestions": ["사장님이 바로 실행할 개선 제안"]
}

규칙:
- 각 배열은 최대 5개까지 작성하세요.
- 추측하지 말고 리뷰에 근거해서 작성하세요.
- suggestions는 실행 가능한 행동으로 작성하세요.

리뷰:
${state.reviews}`
		}
	]);

	const content = Array.isArray(response.content)
		? response.content.map((item) => ('text' in item ? item.text : '')).join('\n')
		: response.content;

	const parsed = JSON.parse(extractJson(content));
	const report = reviewAnalysisReportSchema.parse(parsed);

	return { report };
}

function normalizeReport(state: typeof ReviewState.State) {
	return {
		report: reviewAnalysisReportSchema.parse(state.report ?? {})
	};
}

const graph = new StateGraph(ReviewState)
	.addNode('preprocessReviews', preprocessReviews)
	.addNode('analyzeReviews', analyzeReviews)
	.addNode('normalizeReport', normalizeReport)
	.addEdge(START, 'preprocessReviews')
	.addEdge('preprocessReviews', 'analyzeReviews')
	.addEdge('analyzeReviews', 'normalizeReport')
	.addEdge('normalizeReport', END)
	.compile();

export async function analyzeReviewText(rawReviews: string) {
	const result = await graph.invoke({ rawReviews });

	return reviewAnalysisReportSchema.parse(result.report);
}
