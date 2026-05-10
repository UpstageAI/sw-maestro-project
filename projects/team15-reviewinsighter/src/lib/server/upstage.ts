import { env } from '$env/dynamic/private';
import { ChatOpenAI } from '@langchain/openai';

export function createUpstageModel() {
	const apiKey = env.UPSTAGE_API_KEY;

	if (!apiKey) {
		throw new Error('UPSTAGE_API_KEY is not set. Add it to your .env file.');
	}

	return new ChatOpenAI({
		apiKey,
		model: env.UPSTAGE_MODEL ?? 'solar-pro3',
		temperature: 0.2,
		configuration: {
			baseURL: env.UPSTAGE_BASE_URL ?? 'https://api.upstage.ai/v1/solar'
		}
	});
}
