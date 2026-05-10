import { END, START, Annotation, StateGraph } from '@langchain/langgraph';
import type { ReviewAnalysisReport } from '$lib/types/review';
import { chefRecipeSchema, type ChefRecipe } from '$lib/types/chef';
import { extractJson } from './llmJson';
import { createUpstageModel } from './upstage';

const ChefState = Annotation.Root({
	report: Annotation<ReviewAnalysisReport>,
	recipe: Annotation<ChefRecipe | undefined>
});

async function generateRecipe(state: typeof ChefState.State) {
	const model = createUpstageModel();
	const response = await model.invoke([
		{
			role: 'system',
			content:
				'당신은 배달 음식 품질 개선 전문 요리사입니다. 리뷰 분석 보고서를 바탕으로 음식 품질, 조리 방식, 포장, 배달 후 식감 문제를 개선하는 실행 가능한 레시피를 작성합니다. 반드시 보고서에 나온 문제에 근거하세요. 새 메뉴 창작보다 기존 문제 해결에 집중하세요. 반드시 한국어 JSON만 출력하세요.'
		},
		{
			role: 'user',
			content: `아래 리뷰 분석 보고서를 바탕으로 개선 레시피를 작성하세요.

출력 형식:
{
  "recipeTitle": "개선 레시피 제목",
  "targetIssues": ["해결하려는 리뷰 문제"],
  "ingredients": ["필요한 재료 또는 준비물"],
  "steps": ["실제 매장에서 실행 가능한 조리/포장/운영 단계"],
  "operationalNotes": ["매장 운영 시 주의사항"],
  "expectedImprovements": ["리뷰어가 평가할 수 있는 관찰 가능한 개선 효과"]
}

규칙:
- 반드시 한국어 JSON만 출력하세요.
- 보고서에 나온 문제에 근거해서만 작성하세요.
- 새 메뉴 창작보다 기존 문제 해결에 집중하세요.
- targetIssues는 negatives, recurringIssues, suggestions에서 해결 대상을 뽑으세요.
- steps는 실제 매장에서 실행 가능한 조리, 포장, 운영 단계로 작성하세요.
- expectedImprovements는 리뷰어 에이전트가 다시 평가할 수 있게 관찰 가능한 효과로 작성하세요.
- 각 배열은 최대 5개까지 작성하세요.

리뷰 분석 보고서:
${JSON.stringify(state.report, null, 2)}`
		}
	]);

	const content = Array.isArray(response.content)
		? response.content.map((item) => ('text' in item ? item.text : '')).join('\n')
		: response.content;

	const parsed = JSON.parse(extractJson(content));
	const recipe = chefRecipeSchema.parse(parsed);

	return { recipe };
}

function normalizeRecipe(state: typeof ChefState.State) {
	return {
		recipe: chefRecipeSchema.parse(state.recipe ?? {})
	};
}

const graph = new StateGraph(ChefState)
	.addNode('generateRecipe', generateRecipe)
	.addNode('normalizeRecipe', normalizeRecipe)
	.addEdge(START, 'generateRecipe')
	.addEdge('generateRecipe', 'normalizeRecipe')
	.addEdge('normalizeRecipe', END)
	.compile();

export async function generateChefRecipe(report: ReviewAnalysisReport) {
	const result = await graph.invoke({ report });

	return chefRecipeSchema.parse(result.recipe);
}

export async function improveChefRecipe(
	baseRecipe: string,
	report: ReviewAnalysisReport
) {
	const model = createUpstageModel();
	const response = await model.invoke([
		{
			role: 'system',
			content:
				'당신은 배달 음식 품질 개선 전문 요리사입니다. 기본 레시피와 직전 리뷰 분석을 바탕으로 다음 라운드에서 더 좋은 리뷰를 받도록 레시피를 개선합니다. 반드시 한국어 JSON만 출력하세요.'
		},
		{
			role: 'user',
			content: `기본 레시피의 정체성은 유지하되, 직전 리뷰 분석에서 나온 불만을 줄이고 좋았던 점이 더 늘어나도록 개선 레시피를 작성하세요.

출력 형식:
{
  "recipeTitle": "개선 레시피 제목",
  "targetIssues": ["해결하려는 리뷰 문제"],
  "ingredients": ["필요한 재료 또는 준비물"],
  "steps": ["실제 매장에서 실행 가능한 조리/포장/운영 단계"],
  "operationalNotes": ["매장 운영 시 주의사항"],
  "expectedImprovements": ["리뷰어가 평가할 수 있는 관찰 가능한 개선 효과"]
}

규칙:
- 기본 레시피와 완전히 다른 메뉴로 바꾸지 마세요.
- 직전 분석의 negatives, recurringIssues, suggestions를 우선 해결하세요.
- positives는 유지하거나 강화하세요.
- 각 배열은 최대 5개까지 작성하세요.

기본 레시피:
${baseRecipe}

직전 리뷰 분석:
${JSON.stringify(report, null, 2)}`
		}
	]);

	const content = Array.isArray(response.content)
		? response.content.map((item) => ('text' in item ? item.text : '')).join('\n')
		: response.content;

	return chefRecipeSchema.parse(JSON.parse(extractJson(content)));
}
