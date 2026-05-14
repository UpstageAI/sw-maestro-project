import { z } from 'zod';

export const reviewInputSchema = z.object({
	reviews: z
		.string()
		.trim()
		.min(1, '분석할 리뷰를 입력해 주세요.')
		.max(20_000, '리뷰가 너무 깁니다. 20,000자 이하로 입력해 주세요.')
});

export type ReviewInput = z.infer<typeof reviewInputSchema>;

export const demoInputSchema = z.object({
	baseRecipe: z
		.string()
		.trim()
		.min(1, '요리사의 기본 레시피를 입력해 주세요.')
		.max(20_000, '레시피가 너무 깁니다. 20,000자 이하로 입력해 주세요.'),
	reviewerPreferences: z
		.string()
		.trim()
		.min(1, '리뷰어 취향을 입력해 주세요.')
		.max(10_000, '리뷰어 취향이 너무 깁니다. 10,000자 이하로 입력해 주세요.')
});

export type DemoInput = z.infer<typeof demoInputSchema>;

export const reviewAnalysisReportSchema = z.object({
	summary: z.string().default(''),
	positives: z.array(z.string()).default([]),
	negatives: z.array(z.string()).default([]),
	recurringIssues: z.array(z.string()).default([]),
	suggestions: z.array(z.string()).default([])
});

export type ReviewAnalysisReport = z.infer<typeof reviewAnalysisReportSchema>;

export type AnalyzeReviewsResponse = {
	report: ReviewAnalysisReport;
};

export type AnalyzeReviewsError = {
	error: string;
};
