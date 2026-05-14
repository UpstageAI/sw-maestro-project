<script lang="ts">
	import { enhance } from '$app/forms';
	import type { ActionData } from './$types';
	import type { ReviewerOutput } from '$lib/types/reviewer';

	const sampleRecipe = `레시피 제목: 얼큰 순두부찌개

목표 개선 사항:
- 국물 맛이 밍밍하다는 불만 해소
- 두부 식감 개선 (뭉개지지 않게)

재료:
- 순두부 1팩
- 돼지고기 앞다리살 200g
- 청양고추 2개
- 대파 1대
- 다진 마늘 1큰술
- 고춧가루 2큰술
- 국간장 1큰술
- 멸치 육수 500ml
- 달걀 1개

조리 순서:
1. 멸치 육수를 끓이고 돼지고기를 넣어 중간 불에서 5분간 볶는다.
2. 고춧가루, 다진 마늘, 국간장을 넣고 볶아 베이스 소스를 만든다.
3. 멸치 육수를 부어 끓이고 순두부를 큰 덩어리로 넣는다.
4. 청양고추, 대파를 넣고 5분간 더 끓인다.
5. 달걀을 마지막에 넣고 반숙 상태로 마무리한다.

운영 참고 사항:
- 청양고추는 고객 요청 시 추가/제거 가능
- 달걀은 주문 후 바로 넣어 신선도 유지

기대 개선 효과:
- 국물이 진하고 얼큰해져 만족도 상승
- 두부가 뭉개지지 않아 식감 개선`;

	let { form: actionResult }: { form: ActionData | undefined } = $props();

	let recipeText = $state('');
	let submitting = $state(false);

	let reviews = $derived<ReviewerOutput[]>(
		actionResult && 'reviews' in actionResult ? (actionResult.reviews as ReviewerOutput[]) : []
	);
	let actionError = $derived(
		actionResult && 'error' in actionResult ? (actionResult.error as string) : ''
	);

	function fillSample() {
		recipeText = sampleRecipe;
	}

	function ratingStars(rating: number) {
		return '★'.repeat(rating) + '☆'.repeat(5 - rating);
	}

	function ratingColor(rating: number) {
		if (rating >= 4) return 'text-emerald-600';
		if (rating === 3) return 'text-amber-600';
		return 'text-rose-600';
	}

	function cuisineTag(cuisine: string) {
		const map: Record<string, string> = {
			한식: 'bg-orange-100 text-orange-800',
			일식: 'bg-sky-100 text-sky-800',
			중식: 'bg-red-100 text-red-800',
			양식: 'bg-purple-100 text-purple-800',
			'퓨전/무국적': 'bg-teal-100 text-teal-800'
		};
		return map[cuisine] ?? 'bg-stone-100 text-stone-700';
	}
</script>

<svelte:head>
	<title>Reviewer Agent Test — Review Insighter</title>
</svelte:head>

<main class="min-h-screen bg-stone-950 text-stone-100">
	<section class="mx-auto flex w-full max-w-6xl flex-col gap-8 px-5 py-8 sm:px-8 lg:py-12">
		<header class="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-black/30 md:p-8">
			<p class="w-fit rounded-full border border-sky-300/30 bg-sky-300/10 px-3 py-1 text-sm font-medium text-sky-200">
				Reviewer Agent — MVP 검증용
			</p>
			<div class="mt-4 space-y-2">
				<h1 class="text-4xl font-black tracking-tight text-white sm:text-5xl">리뷰어 에이전트</h1>
				<p class="max-w-2xl text-lg leading-8 text-stone-300">
					요리 레시피를 입력하면 취향이 다른 5명의 리뷰어가 각자의 시각으로 배달앱 리뷰를 작성합니다.
				</p>
			</div>
		</header>

		<form
			method="POST"
			class="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]"
			use:enhance={() => {
				submitting = true;
				return async ({ update }) => {
					await update();
					submitting = false;
				};
			}}
		>
			<section class="rounded-[2rem] border border-white/10 bg-white/[0.06] p-5 sm:p-6">
				<div class="mb-4 flex flex-wrap items-center justify-between gap-3">
					<div>
						<h2 class="text-2xl font-bold text-white">레시피 입력</h2>
						<p class="mt-1 text-sm text-stone-400">요리사 에이전트가 생성한 레시피를 붙여넣으세요.</p>
					</div>
					<button
						type="button"
						class="rounded-full border border-white/15 px-4 py-2 text-sm font-semibold text-stone-200 transition hover:border-sky-200 hover:text-sky-100"
						onclick={fillSample}
					>
						샘플 넣기
					</button>
				</div>

				<textarea
					name="recipeText"
					bind:value={recipeText}
					class="h-96 w-full resize-none rounded-3xl border border-white/10 bg-stone-900/80 p-5 leading-7 text-stone-100 outline-none transition placeholder:text-stone-600 focus:border-sky-300/60 focus:ring-4 focus:ring-sky-300/10"
					placeholder="예: 레시피 제목: 얼큰 순두부찌개&#10;재료: 순두부, 돼지고기...&#10;조리 순서: ..."
				></textarea>

				<div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
					<p class="text-sm text-stone-500">{recipeText.length.toLocaleString()}자 입력됨</p>
					<button
						type="submit"
						class="rounded-full bg-sky-400 px-6 py-3 font-black text-stone-950 transition hover:bg-sky-300 disabled:cursor-not-allowed disabled:opacity-60"
						disabled={submitting}
					>
						{submitting ? '리뷰 생성 중...' : '리뷰 생성'}
					</button>
				</div>

				{#if actionError}
					<p class="mt-4 rounded-2xl border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-100">
						{actionError}
					</p>
				{/if}
			</section>

			<section class="rounded-[2rem] border border-white/10 bg-stone-100 p-5 text-stone-950 sm:p-6">
				<div class="mb-5">
					<p class="text-sm font-bold uppercase tracking-[0.2em] text-sky-700">Reviewer Output</p>
					<h2 class="mt-2 text-3xl font-black">리뷰어 반응</h2>
				</div>

				{#if reviews.length > 0}
					<div class="space-y-4">
						{#each reviews as reviewer}
							<article class="rounded-3xl bg-white p-5 shadow-sm">
								<div class="flex flex-wrap items-start justify-between gap-2">
									<div class="flex items-center gap-2">
										<span class="text-lg font-black">{reviewer.reviewerName}</span>
										<span class="rounded-full px-2 py-0.5 text-xs font-semibold {cuisineTag(reviewer.preferredCuisine)}">
											{reviewer.preferredCuisine}
										</span>
									</div>
									<div class="flex items-center gap-1">
										<span class="text-base {ratingColor(reviewer.rating)}">{ratingStars(reviewer.rating)}</span>
										<span class="text-sm font-bold {ratingColor(reviewer.rating)}">{reviewer.rating}/5</span>
									</div>
								</div>
								<p class="mt-3 leading-7 text-stone-700">{reviewer.review}</p>
							</article>
						{/each}

						<details class="rounded-3xl bg-white p-5 shadow-sm">
							<summary class="cursor-pointer text-sm font-semibold text-stone-500">
								Raw JSON 보기
							</summary>
							<pre class="mt-3 overflow-x-auto rounded-2xl bg-stone-100 p-4 text-xs text-stone-700">{JSON.stringify(reviews, null, 2)}</pre>
						</details>
					</div>
				{:else}
					<div class="flex min-h-80 items-center justify-center rounded-3xl border border-dashed border-stone-300 bg-white/70 p-8 text-center">
						<p class="max-w-sm text-stone-500">
							레시피를 입력하고 리뷰 생성 버튼을 누르면 취향이 다른 리뷰어들의 반응이 표시됩니다.
						</p>
					</div>
				{/if}
			</section>
		</form>
	</section>
</main>
