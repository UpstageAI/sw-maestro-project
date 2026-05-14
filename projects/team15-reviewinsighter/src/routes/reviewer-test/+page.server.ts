import { fail } from '@sveltejs/kit';
import { generateRecipeReviews } from '$lib/server/reviewerGraph';
import type { Actions } from './$types';

export const actions: Actions = {
	default: async ({ request }) => {
		const formData = await request.formData();
		const recipeText = formData.get('recipeText')?.toString() ?? '';

		if (!recipeText.trim()) {
			return fail(400, { error: '레시피를 입력해 주세요.', recipeText });
		}

		if (recipeText.length > 10_000) {
			return fail(400, { error: '레시피가 너무 깁니다. 10,000자 이하로 입력해 주세요.', recipeText });
		}

		try {
			const reviews = await generateRecipeReviews(recipeText);
			return { reviews, recipeText };
		} catch (error) {
			console.error(error);
			return fail(500, {
				error: '리뷰 생성 중 오류가 발생했습니다. API 키와 입력 내용을 확인해 주세요.',
				recipeText
			});
		}
	}
};
