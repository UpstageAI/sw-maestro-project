export const API_BASE = 'http://127.0.0.1:8000/api/v1';

export const SAVE_SLOT_PREFIX = 'SaveLabel';
export const SAVE_SLOT_ID = 1;
export const SAVE_SLOT_KEY = 'Save_1';
export const SAVE_SLOT_NAME = 'In Progress';
// 자동 저장은 playing=true 인 동안 모든 라벨에서 발생.
export const CHAT_RESUME_LABELS = new Set (['LLMChat']);
export const RESUME_SLOT_SAVE_DELAY_MS = 180;

export function finiteNumber (value, fallback = 0) {
	if (typeof value === 'number' && Number.isFinite (value)) return value;
	if (typeof value === 'string' && value.trim () !== '') {
		const n = Number (value);
		if (Number.isFinite (n)) return n;
	}
	return fallback;
}

export const SERA_SPRITE_MAP = {
	NEUTRAL:   'calm',
	HAPPY:     'happy',
	EXCITED:   'excited',
	SHY:       'shy',
	SAD:       'sad',
	ANGRY:     'angry',
	DISGUSTED: 'disgust',
	FURIOUS:   'angry'
};
export const SERA_SPRITE_FILE = {
	calm:    '평온.png',
	happy:   '행복.png',
	excited: '흥분(좋은의미).png',
	shy:     '수줍음.png',
	sad:     '슬픔.png',
	angry:   '화남.png',
	disgust: '혐오.png'
};
export const SERA_FADE_MS = {
	NEUTRAL: 350, HAPPY: 450, EXCITED: 350, SHY: 400, SAD: 400,
	ANGRY: 180, DISGUSTED: 180, FURIOUS: 180
};

export function spriteUrl (spriteKey) {
	const file = SERA_SPRITE_FILE[spriteKey] || SERA_SPRITE_FILE.calm;
	return `assets/characters/이세라_표정/이세라_표정/${encodeURI (file)}`;
}

export function escapeDialogText (text) {
	return String (text)
		.replace (/&/g, '&amp;')
		.replace (/</g, '&lt;')
		.replace (/>/g, '&gt;')
		.replace (/"/g, '&quot;')
		.replace (/'/g, '&#039;')
		.replace (/\r?\n/g, '<br>');
}

export const EVENT_LABELS = {
	EVENT_LIKE_P30:  { sign: '+', text: '호감도 +30 도달' },
	EVENT_LIKE_P50:  { sign: '+', text: '호감도 +50 도달' },
	EVENT_LIKE_P70:  { sign: '+', text: '호감도 +70 도달' },
	EVENT_LIKE_P100: { sign: '+', text: '호감도 +100 도달' },
	EVENT_DISLIKE_M30: { sign: '−', text: '호감도 -30 도달' },
	EVENT_DISLIKE_M50: { sign: '−', text: '호감도 -50 도달' },
	EVENT_DISLIKE_M70: { sign: '−', text: '호감도 -70 도달' }
};

export const SCENE_BG_KEY = {
	SCENE_INTRO:                     'fade_black',
	SCENE_FIRST_MEET:                's1_room',
	SCENE_PROJECT_PLAN_EVALUATION:   'scene_project_plan_evaluation',
	SCENE_LAUNCH_CEREMONY:           'scene_launch_ceremony',
	SCENE_MID_EVALUATION:            'scene_mid_evaluation',
	SCENE_DEEP_DEV:                  'scene_deep_dev',
	SCENE_FINAL_EVALUATION:          'scene_final_evaluation',
	SCENE_GRADUATION_BUSAN:          'scene_graduation_busan',
	SCENE_ENDING_INSTANT_BAD:        'scene_ending_instant_bad',
	SCENE_ENDING_BAD:                'scene_ending_bad',
	SCENE_ENDING_NORMAL_NO_CONTACT:  'scene_ending_normal_no_contact',
	SCENE_ENDING_NORMAL_CONTACT:     'scene_ending_normal_contact',
	SCENE_ENDING_HAPPY:              'scene_ending_happy',
	SCENE_ENDING_MARRIAGE:           'scene_ending_marriage'
};
