import { fail } from '@sveltejs/kit';
import { generateChefRecipe } from '$lib/server/chefGraph';
import { reviewAnalysisReportSchema, type ReviewAnalysisReport } from '$lib/types/review';
import type { Actions } from './$types';

export const actions: Actions = {
	default: async ({ request }) => {
		const formData = await request.formData();
		const reportText = String(formData.get('report') ?? '');
		let report: ReviewAnalysisReport;

		try {
			report = reviewAnalysisReportSchema.parse(JSON.parse(reportText));
		} catch (error) {
			console.error(error);

			return fail(400, {
				error: '보고서 JSON 형식을 확인해 주세요.',
				reportText
			});
		}

		try {
			const recipe = await generateChefRecipe(report);

			return { recipe, reportText };
		} catch (error) {
			console.error(error);

			return fail(500, {
				error: '레시피 생성 중 오류가 발생했습니다. API 키 설정과 모델 응답을 확인해 주세요.',
				reportText
			});
		}
	}
};
