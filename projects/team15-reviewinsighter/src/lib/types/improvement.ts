import type { ChefRecipe } from './chef';
import type { ReviewAnalysisReport } from './review';
import type { ReviewerOutput } from './reviewer';

export type ChefAgentState = {
	name: string;
	role: string;
	baseRecipe: string;
};

export type ReviewerAgentState = {
	preferences: string;
};

export type ImprovementCycle = {
	round: number;
	inputReport: ReviewAnalysisReport;
	chefRecipe: ChefRecipe;
	reviewerReviews: ReviewerOutput[];
	analysisReport?: ReviewAnalysisReport;
	averageRating: number;
	ratingDelta: number;
	positiveCount: number;
	negativeCount: number;
};

export type ReviewImprovementFlow = {
	initialChefState: ChefAgentState;
	initialReviewerState: ReviewerAgentState;
	baseReviewerReviews: ReviewerOutput[];
	baseAnalysisReport: ReviewAnalysisReport;
	baseAverageRating: number;
	cycles: ImprovementCycle[];
};
