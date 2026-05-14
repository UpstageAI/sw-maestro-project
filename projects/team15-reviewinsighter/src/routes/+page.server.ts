import { fail } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod4 } from 'sveltekit-superforms/adapters';
import { generateReviewImprovementFlow } from '$lib/server/improvementGraph';
import { demoInputSchema } from '$lib/types/review';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	return {
		form: await superValidate(zod4(demoInputSchema))
	};
};

export const actions: Actions = {
	default: async ({ request }) => {
		const form = await superValidate(request, zod4(demoInputSchema));

		if (!form.valid) {
			return fail(400, { form });
		}

		try {
			const flow = await generateReviewImprovementFlow(form.data);

			return { form, flow };
		} catch (error) {
			console.error(error);

			return fail(500, {
				form,
				error: '개선 플로우 생성 중 오류가 발생했습니다. API 키와 입력 내용을 확인해 주세요.'
			});
		}
	}
};
