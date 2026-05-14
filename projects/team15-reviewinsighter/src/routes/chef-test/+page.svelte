<script lang="ts">
	import type { ChefRecipe } from '$lib/types/chef';
	import type { ActionData } from './$types';

	const sampleReport = {
		summary:
			'맛과 양, 반찬 구성은 긍정적이지만 배달 지연, 음식 온도 저하, 국물 누수, 튀김 식감 저하가 반복적으로 언급됩니다.',
		positives: ['양이 넉넉하고 고기가 부드럽다', '포장이 깔끔하고 반찬이 넉넉하다'],
		negatives: ['배달이 늦어 음식이 식었다', '국물이 포장 밖으로 샜다', '튀김이 눅눅했다'],
		recurringIssues: ['배달 지연으로 인한 온도 저하', '국물 누수', '튀김 식감 저하'],
		suggestions: [
			'국물 용기와 실링 방식을 점검한다',
			'튀김류는 통풍 포장이나 소스 분리 포장을 적용한다',
			'배달 지연 시 안내 메시지를 제공한다'
		]
	};
	const reportPlaceholder =
		'{"summary":"...", "positives":[], "negatives":[], "recurringIssues":[], "suggestions":[]}';

	let { form: actionResult }: { form: ActionData | undefined } = $props();
	// svelte-ignore state_referenced_locally
	let reportText = $state(actionResult?.reportText ?? JSON.stringify(sampleReport, null, 2));
	let recipe = $derived<ChefRecipe | null>(actionResult?.recipe ?? null);
	let actionError = $derived(actionResult && 'error' in actionResult ? actionResult.error : '');

	function fillSampleReport() {
		reportText = JSON.stringify(sampleReport, null, 2);
	}
</script>

<svelte:head>
	<title>Chef Agent Test</title>
	<meta name="description" content="리뷰 분석 보고서로 요리사 에이전트 개선 레시피를 검증합니다." />
</svelte:head>

<main class="min-h-screen bg-stone-950 text-stone-100">
	<section class="mx-auto flex w-full max-w-6xl flex-col gap-6 px-5 py-8 sm:px-8 lg:py-12">
		<header class="flex flex-col gap-3 border-b border-white/10 pb-6">
			<p class="text-sm font-bold uppercase tracking-[0.2em] text-amber-200">Chef Agent Test</p>
			<h1 class="text-3xl font-black text-white sm:text-4xl">요리사 에이전트 검증</h1>
			<p class="max-w-3xl leading-7 text-stone-300">
				리뷰 분석 보고서 JSON만 입력해 개선 레시피 산출물을 확인합니다.
			</p>
		</header>

		<form method="POST" class="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
			<section class="rounded-2xl border border-white/10 bg-white/[0.06] p-5 sm:p-6">
				<div class="mb-4 flex flex-wrap items-center justify-between gap-3">
					<div>
						<h2 class="text-xl font-bold text-white">분석 보고서 JSON</h2>
						<p class="mt-1 text-sm text-stone-400">ReviewAnalysisReport 형식으로 입력하세요.</p>
					</div>
					<button
						type="button"
						class="rounded-full border border-white/15 px-4 py-2 text-sm font-semibold text-stone-200 transition hover:border-amber-200 hover:text-amber-100"
						onclick={fillSampleReport}
					>
						샘플 넣기
					</button>
				</div>

				<textarea
					name="report"
					bind:value={reportText}
					class="h-[32rem] w-full resize-none rounded-2xl border border-white/10 bg-stone-900/80 p-5 font-mono text-sm leading-6 text-stone-100 outline-none transition placeholder:text-stone-600 focus:border-amber-300/60 focus:ring-4 focus:ring-amber-300/10"
					placeholder={reportPlaceholder}
				></textarea>

				<div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
					<p class="text-sm text-stone-500">{reportText.length.toLocaleString()}자 입력됨</p>
					<button
						type="submit"
						class="rounded-full bg-amber-300 px-6 py-3 font-black text-stone-950 transition hover:bg-amber-200"
					>
						레시피 생성
					</button>
				</div>

				{#if actionError}
					<p class="mt-4 rounded-2xl border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-100">
						{actionError}
					</p>
				{/if}
			</section>

			<section class="rounded-2xl border border-white/10 bg-stone-100 p-5 text-stone-950 sm:p-6">
				<div class="mb-5">
					<p class="text-sm font-bold uppercase tracking-[0.2em] text-amber-700">Chef Recipe</p>
					<h2 class="mt-2 text-2xl font-black">개선 레시피</h2>
				</div>

				{#if recipe}
					<div class="space-y-4">
						<article class="rounded-2xl bg-white p-5 shadow-sm">
							<h3 class="font-black">레시피 제목</h3>
							<p class="mt-2 leading-7 text-stone-700">{recipe.recipeTitle}</p>
						</article>

						<div class="grid gap-4 sm:grid-cols-2">
							{@render RecipeList('해결 대상', recipe.targetIssues)}
							{@render RecipeList('재료와 준비물', recipe.ingredients)}
						</div>

						{@render RecipeList('실행 단계', recipe.steps)}
						{@render RecipeList('운영 노트', recipe.operationalNotes)}
						{@render RecipeList('기대 개선 효과', recipe.expectedImprovements)}

						<details class="rounded-2xl bg-white p-5 shadow-sm">
							<summary class="cursor-pointer font-black">원본 JSON</summary>
							<pre class="mt-4 overflow-auto rounded-xl bg-stone-950 p-4 text-xs leading-5 text-stone-100">{JSON.stringify(recipe, null, 2)}</pre>
						</details>
					</div>
				{:else}
					<div
						class="flex min-h-80 items-center justify-center rounded-2xl border border-dashed border-stone-300 bg-white/70 p-8 text-center"
					>
						<p class="max-w-sm text-stone-500">
							보고서 JSON을 넣고 레시피 생성을 누르면 요리사 에이전트 결과가 표시됩니다.
						</p>
					</div>
				{/if}
			</section>
		</form>
	</section>
</main>

{#snippet RecipeList(title: string, items: string[])}
	<article class="rounded-2xl bg-white p-5 shadow-sm">
		<h3 class="font-black">{title}</h3>
		{#if items.length > 0}
			<ol class="mt-3 space-y-2">
				{#each items as item}
					<li class="rounded-xl bg-stone-100 px-4 py-3 text-sm leading-6 text-stone-800">{item}</li>
				{/each}
			</ol>
		{:else}
			<p class="mt-3 text-sm text-stone-500">생성된 항목이 없습니다.</p>
		{/if}
	</article>
{/snippet}
