import { END, START, Annotation, StateGraph } from '@langchain/langgraph';
import type { DemoInput, ReviewAnalysisReport } from '$lib/types/review';
import type { ImprovementCycle, ReviewImprovementFlow } from '$lib/types/improvement';
import { reviewAnalysisReportSchema } from '$lib/types/review';
import { reviewerResultSchema, type ReviewerOutput } from '$lib/types/reviewer';
import { improveChefRecipe } from './chefGraph';
import { analyzeReviewText } from './reviewGraph';
import { generateRecipeReviews } from './reviewerGraph';

const CYCLE_COUNT = 3;

const ImprovementState = Annotation.Root({
	baseRecipe: Annotation<string>,
	reviewerPreferences: Annotation<string>,
	baseReviewerReviews: Annotation<ReviewerOutput[] | undefined>,
	baseAnalysisReport: Annotation<ReviewAnalysisReport | undefined>,
	cycles: Annotation<ImprovementCycle[] | undefined>
});

export type ImprovementStreamEvent =
	| { type: 'init'; flow: Pick<ReviewImprovementFlow, 'initialChefState' | 'initialReviewerState'> }
	| { type: 'baseline-reviews'; reviews: ReviewerOutput[]; averageRating: number }
	| { type: 'baseline-analysis'; report: ReviewAnalysisReport }
	| { type: 'cycle'; cycle: ImprovementCycle }
	| { type: 'done'; flow: ReviewImprovementFlow };

function createInitialFlow(input: DemoInput): ReviewImprovementFlow {
	return {
		initialChefState: {
			name: '요리사 에이전트',
			role: '기본 레시피를 유지하면서 리뷰어 반응 분석을 반영해 매 라운드 개선안을 만듭니다.',
			baseRecipe: input.baseRecipe
		},
		initialReviewerState: {
			preferences: input.reviewerPreferences
		},
		baseReviewerReviews: [],
		baseAnalysisReport: reviewAnalysisReportSchema.parse({}),
		baseAverageRating: 0,
		cycles: []
	};
}

function formatReviewerReviews(reviews: ReviewerOutput[]) {
	return reviews
		.map(
			(review) =>
				`${review.reviewerName} (${review.preferredCuisine}, ${review.rating}/5): ${review.review}`
		)
		.join('\n');
}

function averageRating(reviews: ReviewerOutput[]) {
	if (reviews.length === 0) return 0;

	return reviews.reduce((sum, review) => sum + review.rating, 0) / reviews.length;
}

function formatImprovedRecipeForReviewers(recipe: ImprovementCycle['chefRecipe']) {
	return `레시피 제목: ${recipe.recipeTitle}

해결 대상:
${recipe.targetIssues.map((item) => `- ${item}`).join('\n')}

재료와 준비물:
${recipe.ingredients.map((item) => `- ${item}`).join('\n')}

실행 단계:
${recipe.steps.map((item) => `- ${item}`).join('\n')}

운영 노트:
${recipe.operationalNotes.map((item) => `- ${item}`).join('\n')}

기대 개선 효과:
${recipe.expectedImprovements.map((item) => `- ${item}`).join('\n')}`;
}

async function simulateBaseReviews(state: typeof ImprovementState.State) {
	const baseReviewerReviews = await generateRecipeReviews(
		state.baseRecipe,
		state.reviewerPreferences
	);
	const baseAnalysisReport = await analyzeReviewText(formatReviewerReviews(baseReviewerReviews));

	return {
		baseReviewerReviews,
		baseAnalysisReport
	};
}

async function runImprovementCycles(state: typeof ImprovementState.State) {
	let inputReport = reviewAnalysisReportSchema.parse(state.baseAnalysisReport);
	const cycles: ImprovementCycle[] = [];

	for (let round = 1; round <= CYCLE_COUNT; round += 1) {
		const chefRecipe = await improveChefRecipe(state.baseRecipe, inputReport);
		const reviewerReviews = await generateRecipeReviews(
			formatImprovedRecipeForReviewers(chefRecipe),
			state.reviewerPreferences
		);
		const shouldAnalyze = round < CYCLE_COUNT;
		const analysisReport = shouldAnalyze
			? await analyzeReviewText(formatReviewerReviews(reviewerReviews))
			: undefined;
		const cycleAverageRating = averageRating(reviewerReviews);

		cycles.push({
			round,
			inputReport,
			chefRecipe,
			reviewerReviews: reviewerResultSchema.parse({ reviews: reviewerReviews }).reviews,
			analysisReport,
			averageRating: cycleAverageRating,
			ratingDelta: cycleAverageRating - averageRating(state.baseReviewerReviews ?? []),
			positiveCount: analysisReport?.positives.length ?? 0,
			negativeCount: analysisReport?.negatives.length ?? 0
		});

		if (analysisReport) inputReport = analysisReport;
	}

	return { cycles };
}

const graph = new StateGraph(ImprovementState)
	.addNode('simulateBaseReviews', simulateBaseReviews)
	.addNode('runImprovementCycles', runImprovementCycles)
	.addEdge(START, 'simulateBaseReviews')
	.addEdge('simulateBaseReviews', 'runImprovementCycles')
	.addEdge('runImprovementCycles', END)
	.compile();

export async function generateReviewImprovementFlow(input: DemoInput): Promise<ReviewImprovementFlow> {
	const result = await graph.invoke(input);
	const baseReviewerReviews = reviewerResultSchema.parse({ reviews: result.baseReviewerReviews }).reviews;

	return {
		...createInitialFlow(input),
		baseReviewerReviews,
		baseAnalysisReport: reviewAnalysisReportSchema.parse(result.baseAnalysisReport),
		baseAverageRating: averageRating(baseReviewerReviews),
		cycles: result.cycles ?? []
	};
}

export async function* streamReviewImprovementFlow(
	input: DemoInput
): AsyncGenerator<ImprovementStreamEvent> {
	const flow = createInitialFlow(input);

	yield {
		type: 'init',
		flow: {
			initialChefState: flow.initialChefState,
			initialReviewerState: flow.initialReviewerState
		}
	};

	flow.baseReviewerReviews = reviewerResultSchema.parse({
		reviews: await generateRecipeReviews(input.baseRecipe, input.reviewerPreferences)
	}).reviews;
	flow.baseAverageRating = averageRating(flow.baseReviewerReviews);
	yield {
		type: 'baseline-reviews',
		reviews: flow.baseReviewerReviews,
		averageRating: flow.baseAverageRating
	};

	flow.baseAnalysisReport = await analyzeReviewText(formatReviewerReviews(flow.baseReviewerReviews));
	yield { type: 'baseline-analysis', report: flow.baseAnalysisReport };

	let inputReport = flow.baseAnalysisReport;

	for (let round = 1; round <= CYCLE_COUNT; round += 1) {
		const chefRecipe = await improveChefRecipe(input.baseRecipe, inputReport);
		const reviewerReviews = reviewerResultSchema.parse({
			reviews: await generateRecipeReviews(
				formatImprovedRecipeForReviewers(chefRecipe),
				input.reviewerPreferences
			)
		}).reviews;
		const shouldAnalyze = round < CYCLE_COUNT;
		const analysisReport = shouldAnalyze
			? await analyzeReviewText(formatReviewerReviews(reviewerReviews))
			: undefined;
		const cycleAverageRating = averageRating(reviewerReviews);
		const cycle: ImprovementCycle = {
			round,
			inputReport,
			chefRecipe,
			reviewerReviews,
			analysisReport,
			averageRating: cycleAverageRating,
			ratingDelta: cycleAverageRating - flow.baseAverageRating,
			positiveCount: analysisReport?.positives.length ?? 0,
			negativeCount: analysisReport?.negatives.length ?? 0
		};

		flow.cycles = [...flow.cycles, cycle];
		if (analysisReport) inputReport = analysisReport;
		yield { type: 'cycle', cycle };
	}

	yield { type: 'done', flow };
}
