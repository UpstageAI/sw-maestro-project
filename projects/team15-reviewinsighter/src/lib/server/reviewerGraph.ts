import { END, START, Annotation, StateGraph } from '@langchain/langgraph';
import {
	reviewerOutputSchema,
	reviewerPersonas,
	reviewerResultSchema,
	type ReviewerOutput
} from '$lib/types/reviewer';
import { extractJson } from './llmJson';
import { createUpstageModel } from './upstage';

const ReviewerState = Annotation.Root({
	recipeText: Annotation<string>,
	personasText: Annotation<string | undefined>,
	reviews: Annotation<ReviewerOutput[] | undefined>
});

function parsePersonas(personasText?: string) {
	const personas = personasText
		?.split('\n')
		.map((line) => line.trim())
		.filter(Boolean)
		.map((line) => line.replace(/^[-*]\s*/, ''));

	if (personas?.length) return personas;

	return reviewerPersonas.map(
		(persona) => `${persona.name} (선호 음식: ${persona.preferredCuisine}): ${persona.personality}`
	);
}

function getPersonaHint(persona: string) {
	const match = persona.match(/^([^(:：]+)(?:\s*[(:：]([^):：]+)[):：])?\s*[:：]?\s*(.*)$/);

	return {
		name: match?.[1]?.trim() || '리뷰어',
		preferredCuisine: match?.[2]?.replace(/^선호 음식\s*[:：]?\s*/, '').trim() || '',
		description: match?.[3]?.trim() || persona
	};
}

async function generateReviewForPersona(recipeText: string, persona: string) {
	const model = createUpstageModel();
	const hint = getPersonaHint(persona);

	const response = await model.invoke([
		{
			role: 'system',
			content:
				'당신은 배달앱에 음식 리뷰를 남기는 고객입니다. 주어진 인물의 취향과 평가 기준을 반영해 자연스러운 한국어 리뷰를 작성합니다. 반드시 JSON만 출력하세요.'
		},
		{
			role: 'user',
			content: `아래 인물은 주어진 요리 레시피로 만든 음식을 배달 주문해서 먹었습니다. 인물의 취향과 평가 기준을 반영해 자연스러운 배달앱 리뷰를 작성하세요.

페르소나:
${persona}

출력 형식:
{
  "reviewerName": "${hint.name}",
  "preferredCuisine": "${hint.preferredCuisine}",
  "rating": 1~5 정수,
  "review": "리뷰 내용"
}

규칙:
- 인물의 취향, 성격, 평가 기준을 반영하세요.
- 평점은 레시피가 이 페르소나에게 얼마나 맞는지 기준으로 정하세요.
- 리뷰는 실제 배달앱 리뷰처럼 자연스럽고 구체적으로 작성하세요 (50~150자).
- JSON 객체 1개만 출력하세요.

요리 레시피:
${recipeText}`
		}
	]);

	const content = Array.isArray(response.content)
		? response.content.map((item) => ('text' in item ? item.text : '')).join('\n')
		: response.content;

	const review = reviewerOutputSchema.parse(JSON.parse(extractJson(content)));

	return {
		...review,
		reviewerName: review.reviewerName || hint.name,
		preferredCuisine: review.preferredCuisine || hint.preferredCuisine
	};
}

async function generateReviews(state: typeof ReviewerState.State) {
	const personas = parsePersonas(state.personasText);
	const reviews = await Promise.all(
		personas.map((persona) => generateReviewForPersona(state.recipeText, persona))
	);

	return { reviews };
}

function normalizeReviews(state: typeof ReviewerState.State) {
	return {
		reviews: reviewerResultSchema.parse({ reviews: state.reviews ?? [] }).reviews
	};
}

export const reviewerGraph = new StateGraph(ReviewerState)
	.addNode('generateReviews', generateReviews)
	.addNode('normalizeReviews', normalizeReviews)
	.addEdge(START, 'generateReviews')
	.addEdge('generateReviews', 'normalizeReviews')
	.addEdge('normalizeReviews', END)
	.compile();

export async function generateRecipeReviews(recipeText: string, personasText?: string) {
	const result = await reviewerGraph.invoke({ recipeText, personasText });
	return reviewerResultSchema.parse({ reviews: result.reviews }).reviews;
}
