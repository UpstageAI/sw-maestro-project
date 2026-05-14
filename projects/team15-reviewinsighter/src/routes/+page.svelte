<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { ImprovementCycle, ReviewImprovementFlow } from '$lib/types/improvement';
	import type { ReviewAnalysisReport } from '$lib/types/review';
	import type { ReviewerOutput } from '$lib/types/reviewer';
	import type { PageData } from './$types';

	const sampleRecipe = `메뉴: 얼큰 순두부찌개

재료:
- 순두부 1팩
- 돼지고기 앞다리살 120g
- 멸치 육수 500ml
- 고춧가루 0.7큰술
- 다진 마늘 0.5큰술
- 국간장 0.5작은술
- 대파, 청양고추, 달걀
- 기본 흰쌀밥

조리:
1. 냄비에 돼지고기, 고춧가루, 마늘을 넣고 30초 정도만 가볍게 볶는다.
2. 멸치 육수를 넣고 끓으면 순두부를 숟가락으로 크게 떠 넣는다.
3. 대파와 청양고추를 넣고 2분 더 끓인다.
4. 달걀을 바로 풀어 넣고 불을 끈 뒤 배달 용기에 담는다.
5. 간은 따로 보지 않고 바로 출고한다.
6. 밥은 별도 보온 처리 없이 일반 용기에 담는다.

포장:
- 일반 국물 용기에 95% 정도 채운다.
- 랩 실링 없이 뚜껑만 닫고 비닐 봉투에 포장한다.
- 국물과 밥 외 별도 반찬은 김치 1종만 제공한다.
- 배달 예상 시간이 길어도 보온팩은 사용하지 않는다.

현재 의도:
- 빠르게 조리해서 회전율을 높인다.
- 자극적이지 않은 무난한 맛을 목표로 한다.
- 포장 단가를 낮게 유지한다.`;

	const samplePreferences = `- 김민준 (한식): 진한 국물, 넉넉한 양, 빠른 배달을 중요하게 본다. 음식이 식거나 양이 적으면 낮게 평가한다.
- 박소연 (일식): 깔끔한 맛, 신선함, 과하지 않은 간을 선호한다. 포장 상태와 보기 좋은 구성도 중요하다.
- 이도현 (중식): 강한 감칠맛과 푸짐함을 좋아한다. 맛이 분명하면 높은 점수를 준다.
- 정유리 (양식): SNS에 올릴 만한 비주얼과 특별한 경험을 선호한다. 포장이 예쁘면 호감도가 오른다.
- 최현우 (퓨전/무국적): 맛의 밸런스, 조리 완성도, 배달 후 식감을 냉정하게 평가한다.`;

	let { data }: { data: PageData } = $props();

	// svelte-ignore state_referenced_locally
	const { form, errors } = superForm(data.form, { resetForm: false });

	let flow = $state<ReviewImprovementFlow | null>(null);
	let actionError = $state('');
	let streaming = $state(false);
	let progress = $state('');
	let lastCycle = $derived(flow?.cycles.at(-1) ?? null);

	function fillSample() {
		$form.baseRecipe = sampleRecipe;
		$form.reviewerPreferences = samplePreferences;
	}

	function createEmptyFlow(): ReviewImprovementFlow {
		return {
			initialChefState: {
				name: '요리사 에이전트',
				role: '기본 레시피를 유지하면서 리뷰어 반응 분석을 반영해 매 라운드 개선안을 만듭니다.',
				baseRecipe: $form.baseRecipe
			},
			initialReviewerState: {
				preferences: $form.reviewerPreferences
			},
			baseReviewerReviews: [],
			baseAnalysisReport: {
				summary: '',
				positives: [],
				negatives: [],
				recurringIssues: [],
				suggestions: []
			},
			baseAverageRating: 0,
			cycles: []
		};
	}

	function applyStreamEvent(eventName: string, payload: any) {
		if (eventName === 'init') {
			flow = { ...createEmptyFlow(), ...payload.flow };
			progress = '초기 에이전트 상태를 준비했습니다.';
			return;
		}

		if (!flow) flow = createEmptyFlow();

		if (eventName === 'baseline-reviews') {
			flow = {
				...flow,
				baseReviewerReviews: payload.reviews,
				baseAverageRating: payload.averageRating
			};
			progress = '기본 레시피에 대한 리뷰어 평가가 도착했습니다.';
			return;
		}

		if (eventName === 'baseline-analysis') {
			flow = { ...flow, baseAnalysisReport: payload.report };
			progress = '기본 레시피 리뷰 분석이 완료됐습니다.';
			return;
		}

		if (eventName === 'cycle') {
			flow = { ...flow, cycles: [...flow.cycles, payload.cycle] };
			progress = `개선 라운드 ${payload.cycle.round} 결과가 도착했습니다.`;
			return;
		}

		if (eventName === 'done') {
			flow = payload.flow;
			progress = '개선 시뮬레이션이 완료됐습니다.';
			return;
		}

		if (eventName === 'error') {
			actionError = payload.error ?? '스트리밍 중 오류가 발생했습니다.';
		}
	}

	function readSseChunk(chunk: string, onEvent: (eventName: string, payload: unknown) => void) {
		for (const block of chunk.split('\n\n')) {
			if (!block.trim()) continue;

			const eventName = block.match(/^event: (.+)$/m)?.[1] ?? 'message';
			const data = block
				.split('\n')
				.filter((line) => line.startsWith('data: '))
				.map((line) => line.slice(6))
				.join('\n');

			if (data) onEvent(eventName, JSON.parse(data));
		}
	}

	async function runSimulation() {
		actionError = '';
		progress = '';

		if (!$form.baseRecipe.trim() || !$form.reviewerPreferences.trim()) {
			actionError = '기본 레시피와 리뷰어 취향을 모두 입력해 주세요.';
			return;
		}

		streaming = true;
		flow = createEmptyFlow();

		try {
			const response = await fetch('/api/simulate', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					baseRecipe: $form.baseRecipe,
					reviewerPreferences: $form.reviewerPreferences
				})
			});

			if (!response.ok || !response.body) {
				const body = await response.json().catch(() => null);
				throw new Error(body?.error ?? '스트림을 시작하지 못했습니다.');
			}

			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const boundary = buffer.lastIndexOf('\n\n');

				if (boundary === -1) continue;

				const ready = buffer.slice(0, boundary + 2);
				buffer = buffer.slice(boundary + 2);
				readSseChunk(ready, applyStreamEvent);
			}

			if (buffer.trim()) readSseChunk(buffer, applyStreamEvent);
		} catch (error) {
			actionError = error instanceof Error ? error.message : '스트리밍 중 오류가 발생했습니다.';
		} finally {
			streaming = false;
		}
	}

	function toneClass(tone: 'positive' | 'negative' | 'issue' | 'suggestion') {
		return {
			positive: 'bg-emerald-50 text-emerald-900',
			negative: 'bg-rose-50 text-rose-900',
			issue: 'bg-orange-50 text-orange-950',
			suggestion: 'bg-stone-950 text-stone-50'
		}[tone];
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

	function formatDelta(delta: number) {
		return `${delta >= 0 ? '+' : ''}${delta.toFixed(1)}`;
	}
</script>

<svelte:head>
	<title>Review Insighter</title>
	<meta name="description" content="기본 레시피와 리뷰어 취향에서 출발해 반복 개선 사이클을 시연합니다." />
</svelte:head>

<main class="min-h-screen bg-stone-950 text-stone-100">
	<section class="mx-auto flex w-full max-w-7xl flex-col gap-8 px-5 py-8 sm:px-8 lg:py-12">
		<header class="grid gap-5 rounded-[2rem] border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-black/30 md:grid-cols-[1.15fr_0.85fr] md:p-8">
			<div class="space-y-4">
				<p class="w-fit rounded-full border border-amber-300/30 bg-amber-300/10 px-3 py-1 text-sm font-medium text-amber-200">
					Recipe Simulation Flow
				</p>
				<h1 class="text-4xl font-black tracking-tight text-white sm:text-5xl">
					기본 레시피를 리뷰어 반응으로 개선합니다
				</h1>
				<p class="max-w-3xl text-lg leading-8 text-stone-300">
					초기 입력은 리뷰가 아니라 요리사의 기본 레시피와 리뷰어들의 취향입니다. 리뷰어가 먼저 기본 레시피를 평가하고, 그 분석을 바탕으로 요리사가 개선안을 반복합니다.
				</p>
			</div>

			<div class="rounded-3xl bg-amber-300 p-5 text-stone-950">
				<p class="text-sm font-bold uppercase tracking-[0.2em] text-stone-700">Demo Loop</p>
				<ol class="mt-4 space-y-3 text-sm font-semibold">
					<li>1. 기본 레시피 입력</li>
					<li>2. 리뷰어 취향 입력</li>
					<li>3. 기본 레시피 리뷰 생성/분석</li>
					<li>4. 요리사 → 리뷰어 → 분석 반복</li>
				</ol>
			</div>
		</header>

		<form
			method="POST"
			onsubmit={(event) => {
				event.preventDefault();
				runSimulation();
			}}
			class="grid gap-6"
		>
			<section class="space-y-5 rounded-[2rem] border border-white/10 bg-white/[0.06] p-5 sm:p-6">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div>
						<h2 class="text-2xl font-bold text-white">초기 상태 입력</h2>
						<p class="mt-1 text-sm text-stone-400">요리사의 기본 레시피와 리뷰어 취향을 입력하세요.</p>
					</div>
					<button type="button" class="rounded-full border border-white/15 px-4 py-2 text-sm font-semibold text-stone-200 transition hover:border-amber-200 hover:text-amber-100" onclick={fillSample}>
						샘플 넣기
					</button>
				</div>

				<label class="block">
					<span class="mb-2 block font-bold text-white">요리사의 기본 레시피</span>
					<textarea name="baseRecipe" bind:value={$form.baseRecipe} class="h-72 w-full resize-none rounded-3xl border border-white/10 bg-stone-900/80 p-5 leading-7 text-stone-100 outline-none transition placeholder:text-stone-600 focus:border-amber-300/60 focus:ring-4 focus:ring-amber-300/10" placeholder="메뉴, 재료, 조리 순서, 포장 방식을 입력하세요."></textarea>
				</label>
				{#if $errors.baseRecipe}
					<p class="rounded-2xl border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-100">{$errors.baseRecipe[0]}</p>
				{/if}

				<label class="block">
					<span class="mb-2 block font-bold text-white">리뷰어 취향</span>
					<textarea name="reviewerPreferences" bind:value={$form.reviewerPreferences} class="h-56 w-full resize-none rounded-3xl border border-white/10 bg-stone-900/80 p-5 leading-7 text-stone-100 outline-none transition placeholder:text-stone-600 focus:border-amber-300/60 focus:ring-4 focus:ring-amber-300/10" placeholder="리뷰어 이름, 선호 음식, 평가 기준을 목록으로 입력하세요."></textarea>
				</label>
				{#if $errors.reviewerPreferences}
					<p class="rounded-2xl border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-100">{$errors.reviewerPreferences[0]}</p>
				{/if}

				<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
					<p class="text-sm text-stone-500">레시피 {$form.baseRecipe.length.toLocaleString()}자 / 리뷰어 {$form.reviewerPreferences.length.toLocaleString()}자</p>
					<button type="submit" class="inline-flex items-center justify-center gap-2 rounded-full bg-amber-300 px-6 py-3 font-black text-stone-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-60" disabled={streaming}>
						{#if streaming}
							<span class="h-4 w-4 animate-spin rounded-full border-2 border-stone-950/30 border-t-stone-950"></span>
						{/if}
						{streaming ? '시뮬레이션 중...' : '개선 사이클 실행'}
					</button>
				</div>

				{#if progress}
					<p class="rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4 text-sm text-amber-100">{progress}</p>
				{/if}

				{#if actionError}
					<p class="rounded-2xl border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-100">{actionError}</p>
				{/if}
			</section>

			<section class="rounded-[2rem] border border-white/10 bg-stone-100 p-5 text-stone-950 sm:p-6">
				<div class="mb-5 flex flex-wrap items-end justify-between gap-3">
					<div>
						<p class="text-sm font-bold uppercase tracking-[0.2em] text-amber-700">Simulation Result</p>
						<h2 class="mt-2 text-3xl font-black">레시피 개선 시뮬레이션</h2>
					</div>
					{#if lastCycle}
						<p class="rounded-full bg-stone-950 px-4 py-2 text-sm font-black text-stone-50">최종 평점 {lastCycle.averageRating.toFixed(1)} / 5</p>
					{/if}
				</div>

				{#if flow}
					<div class="space-y-5">
						<section class="grid gap-4">
							<article class="rounded-3xl bg-stone-950 p-5 text-stone-50">
								<p class="text-xs font-black uppercase tracking-[0.2em] text-amber-300">Initial Chef</p>
								<h3 class="mt-2 text-2xl font-black">{flow.initialChefState.name}</h3>
								<p class="mt-3 leading-7 text-stone-300">{flow.initialChefState.role}</p>
								<pre class="mt-4 max-h-80 overflow-auto rounded-2xl bg-white/10 p-4 text-xs leading-5 text-stone-100">{flow.initialChefState.baseRecipe}</pre>
							</article>
							<article class="rounded-3xl bg-white p-5 shadow-sm">
								<p class="text-xs font-black uppercase tracking-[0.2em] text-sky-700">Initial Reviewers</p>
								<h3 class="mt-2 text-2xl font-black">리뷰어 취향</h3>
								<pre class="mt-4 max-h-80 overflow-auto rounded-2xl bg-stone-100 p-4 text-xs leading-5 text-stone-700">{flow.initialReviewerState.preferences}</pre>
							</article>
						</section>

						<section class="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-stone-200">
							<div class="flex flex-wrap items-center justify-between gap-3">
								<div>
									<p class="text-xs font-black uppercase tracking-[0.2em] text-stone-500">Baseline</p>
									<h3 class="mt-2 text-2xl font-black">기본 레시피 리뷰어 평가</h3>
								</div>
								<p class="rounded-full bg-stone-950 px-3 py-1 text-sm font-black text-white">평균 {flow.baseAverageRating.toFixed(1)} / 5</p>
							</div>
							<div class="mt-4 space-y-3">{#each flow.baseReviewerReviews as reviewer}{@render ReviewerCard(reviewer)}{/each}</div>
						</section>

						{@render ReportBlock('Baseline Analysis', '기본 레시피 리뷰 분석', flow.baseAnalysisReport)}

						{#each flow.cycles as cycle}{@render CycleBlock(cycle)}{/each}

						{#if streaming}
							<section class="rounded-3xl border border-amber-200 bg-amber-50 p-5 text-amber-950 shadow-sm">
								<div class="flex items-center gap-4">
									<span class="h-7 w-7 animate-spin rounded-full border-4 border-amber-200 border-t-amber-700"></span>
									<div>
										<p class="text-sm font-black uppercase tracking-[0.2em] text-amber-700">Running</p>
										<p class="mt-1 font-bold">{progress || '에이전트 시뮬레이션을 시작하는 중입니다.'}</p>
									</div>
								</div>
								<div class="mt-4 h-2 overflow-hidden rounded-full bg-amber-100">
									<div class="h-full w-1/2 animate-pulse rounded-full bg-amber-500"></div>
								</div>
							</section>
						{/if}
					</div>
				{:else}
					<div class="flex min-h-96 items-center justify-center rounded-3xl border border-dashed border-stone-300 bg-white/70 p-8 text-center">
						<p class="max-w-md text-stone-500">기본 레시피와 리뷰어 취향을 입력하면 기본 평가부터 3회의 개선 라운드까지 표시됩니다.</p>
					</div>
				{/if}
			</section>
		</form>
	</section>
</main>

{#snippet CycleBlock(cycle: ImprovementCycle)}
	<section class="overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-stone-200">
		<div class="bg-stone-950 p-5 text-stone-50">
			<p class="text-xs font-black uppercase tracking-[0.2em] text-amber-300">Round {cycle.round}</p>
			<h3 class="mt-2 text-2xl font-black">요리사 개선안: {cycle.chefRecipe.recipeTitle}</h3>
			<p class="mt-2 text-sm text-stone-300">평균 평점 {cycle.averageRating.toFixed(1)} / 5</p>
			<div class="mt-4 grid gap-4">{@render DarkList('해결 대상', cycle.chefRecipe.targetIssues)}{@render DarkList('실행 단계', cycle.chefRecipe.steps)}</div>
		</div>
		<div class="grid gap-5 p-5">
			<section><p class="text-xs font-black uppercase tracking-[0.2em] text-sky-700">Reviewer Feedback</p><div class="mt-3 space-y-3">{#each cycle.reviewerReviews as reviewer}{@render ReviewerCard(reviewer)}{/each}</div></section>
			{#if cycle.analysisReport}
				{@render ReportBlock('Analysis After Round', `Round ${cycle.round} 리뷰 분석`, cycle.analysisReport)}
			{:else}
				<section class="rounded-3xl bg-emerald-50 p-5 text-emerald-950 shadow-sm ring-1 ring-emerald-100">
					<p class="text-xs font-black uppercase tracking-[0.2em] text-emerald-700">Final Comparison</p>
					<h3 class="mt-2 text-2xl font-black">초기 평점 대비 변화</h3>
					<p class="mt-4 text-5xl font-black">{formatDelta(cycle.ratingDelta)}</p>
					<p class="mt-3 leading-7 text-emerald-800">
						마지막 사이클은 다음 개선을 위한 분석을 생략하고, 기본 레시피 평가 대비 평점 변화만 비교합니다.
					</p>
				</section>
			{/if}
		</div>
	</section>
{/snippet}

{#snippet ReviewerCard(reviewer: ReviewerOutput)}
	<article class="rounded-2xl bg-stone-100 p-4"><div class="flex flex-wrap items-start justify-between gap-2"><div class="flex items-center gap-2"><span class="font-black">{reviewer.reviewerName}</span><span class="rounded-full px-2 py-0.5 text-xs font-semibold {cuisineTag(reviewer.preferredCuisine)}">{reviewer.preferredCuisine}</span></div><div class="flex items-center gap-1"><span class="text-sm {ratingColor(reviewer.rating)}">{ratingStars(reviewer.rating)}</span><span class="text-sm font-black {ratingColor(reviewer.rating)}">{reviewer.rating}/5</span></div></div><p class="mt-3 leading-7 text-stone-700">{reviewer.review}</p></article>
{/snippet}

{#snippet ReportBlock(step: string, title: string, report: ReviewAnalysisReport)}
	<section class="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-stone-200"><p class="text-xs font-black uppercase tracking-[0.2em] text-amber-700">{step}</p><h3 class="mt-2 text-2xl font-black">{title}</h3><p class="mt-3 leading-7 text-stone-700">{report.summary}</p><div class="mt-4 grid gap-4">{@render ReportList('좋았던 점', report.positives, 'positive')}{@render ReportList('아쉬웠던 점', report.negatives, 'negative')}</div><div class="mt-4 space-y-4">{@render ReportList('반복되는 문제', report.recurringIssues, 'issue')}{@render ReportList('개선 제안', report.suggestions, 'suggestion')}</div></section>
{/snippet}

{#snippet ReportList(title: string, items: string[], tone: 'positive' | 'negative' | 'issue' | 'suggestion')}
	<article class="rounded-2xl bg-stone-100 p-4"><h4 class="font-black">{title}</h4>{#if items.length > 0}<ul class="mt-3 space-y-2">{#each items as item}<li class="rounded-xl px-4 py-3 text-sm leading-6 {toneClass(tone)}">{item}</li>{/each}</ul>{:else}<p class="mt-3 text-sm text-stone-500">분석된 항목이 없습니다.</p>{/if}</article>
{/snippet}

{#snippet DarkList(title: string, items: string[])}
	<article class="rounded-2xl bg-white/10 p-4 ring-1 ring-white/10"><h4 class="font-black text-white">{title}</h4>{#if items.length > 0}<ol class="mt-3 space-y-2">{#each items as item}<li class="rounded-xl bg-white px-4 py-3 text-sm leading-6 text-stone-800">{item}</li>{/each}</ol>{:else}<p class="mt-3 text-sm text-stone-400">생성된 항목이 없습니다.</p>{/if}</article>
{/snippet}
