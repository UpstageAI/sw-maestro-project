import { z } from 'zod';

export const reviewerPersonas = [
	{
		name: '김민준',
		preferredCuisine: '한식',
		personality:
			'50대 남성 직장인. 자극적이고 진한 국물 맛을 좋아하며 가성비를 매우 중시함. 배달이 느리거나 양이 적으면 바로 불만을 표출하는 편.'
	},
	{
		name: '박소연',
		preferredCuisine: '일식',
		personality:
			'30대 여성 직장인. 깔끔하고 섬세한 맛과 신선한 재료를 중시함. 지나치게 짜거나 자극적인 음식은 선호하지 않으며 플레이팅도 신경 씀.'
	},
	{
		name: '이도현',
		preferredCuisine: '중식',
		personality:
			'40대 남성 사업가. 기름지고 풍부한 감칠맛을 좋아하며 양과 볼륨을 매우 중시함. 맛있으면 단골 될 의향이 있고 단호하게 평가하는 편.'
	},
	{
		name: '정유리',
		preferredCuisine: '양식',
		personality:
			'20대 여성 대학생. 트렌디하고 SNS에 올릴 만한 비주얼과 독특한 맛 조합을 추구함. 가격 대비 경험과 분위기를 중시하며 감성적으로 리뷰 작성.'
	},
	{
		name: '최현우',
		preferredCuisine: '퓨전/무국적',
		personality:
			'30대 남성 식품 블로거. 다양한 음식을 먹어봐서 맛에 대한 기준이 높음. 냉정하고 분석적으로 맛의 밸런스, 재료 품질, 조리 완성도를 평가함.'
	}
] as const;

export const reviewerOutputSchema = z.object({
	reviewerName: z.string().default(''),
	preferredCuisine: z.string().default(''),
	rating: z.number().min(1).max(5).default(3),
	review: z.string().default('')
});

export const reviewerResultSchema = z.object({
	reviews: z.array(reviewerOutputSchema).default([])
});

export type ReviewerOutput = z.infer<typeof reviewerOutputSchema>;
export type ReviewerResult = z.infer<typeof reviewerResultSchema>;
