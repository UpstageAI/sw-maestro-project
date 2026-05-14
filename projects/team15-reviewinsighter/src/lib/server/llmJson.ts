export function extractJson(text: string) {
	const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i)?.[1];
	const candidate = fenced ?? text;
	const start = candidate.indexOf('{');
	const end = candidate.lastIndexOf('}');

	if (start === -1 || end === -1 || end <= start) {
		throw new Error('AI response did not include JSON.');
	}

	return candidate.slice(start, end + 1);
}
