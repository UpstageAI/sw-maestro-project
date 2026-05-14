import { json } from '@sveltejs/kit';
import { streamReviewImprovementFlow } from '$lib/server/improvementGraph';
import { demoInputSchema } from '$lib/types/review';
import type { RequestHandler } from './$types';

const encoder = new TextEncoder();

function encodeEvent(event: string, data: unknown) {
	return encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

export const POST: RequestHandler = async ({ request }) => {
	const parsed = demoInputSchema.safeParse(await request.json().catch(() => null));

	if (!parsed.success) {
		return json({ error: '입력값을 확인해 주세요.' }, { status: 400 });
	}

	const stream = new ReadableStream({
		async start(controller) {
			try {
				for await (const event of streamReviewImprovementFlow(parsed.data)) {
					controller.enqueue(encodeEvent(event.type, event));
				}
			} catch (error) {
				console.error(error);
				controller.enqueue(
					encodeEvent('error', {
						error: '개선 플로우 생성 중 오류가 발생했습니다. API 키와 입력 내용을 확인해 주세요.'
					})
				);
			} finally {
				controller.close();
			}
		}
	});

	return new Response(stream, {
		headers: {
			'Content-Type': 'text/event-stream; charset=utf-8',
			'Cache-Control': 'no-cache, no-transform',
			Connection: 'keep-alive'
		}
	});
};
