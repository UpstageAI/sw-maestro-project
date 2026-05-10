import { monogatari } from './engine.js';

// 영구 저장용 변수
monogatari.storage ({
	player: {
		name: '???'
	},
	sera: {
		name: '???'
	},
	llm: {
		prompt: '',
		response: '',
		emotion: 'NEUTRAL',
		event_id: '',
		next_scene_id: '',
		shouldEnd: false
	},
	game: {
		affinity: 0,
		affinity_delta: 0,
		progress: 0,
		chat_count: 0,
		current_scene_id: 'SCENE_FIRST_MEET'
	}
});
