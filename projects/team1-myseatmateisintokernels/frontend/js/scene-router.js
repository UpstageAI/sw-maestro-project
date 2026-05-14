import { monogatari } from './engine.js';

// 씬 라벨에서 'jump LLMChat' 의 인덱스를 찾는다.
// _TransitionDispatch 가 에필로그 시작 step 을 계산할 때 사용.
export function findJumpLLMChatStep (label) {
	if (!label) return -1;
	let arr = null;
	try { if (typeof monogatari.label === 'function') arr = monogatari.label (label); } catch (e) {}
	if (!Array.isArray (arr)) {
		try {
			const all = typeof monogatari.script === 'function' ? monogatari.script () : null;
			if (all && Array.isArray (all[label])) arr = all[label];
		} catch (e) {}
	}
	if (!Array.isArray (arr)) return -1;
	for (let i = 0; i < arr.length; i++) {
		if (arr[i] === 'jump LLMChat') return i;
	}
	return -1;
}

// 씬 라벨 마지막에 호출되는 dispatcher.
// llm.next_scene_id 를 보고 다음 씬 / 엔딩 / 폴백 으로 분기.
// engine 이 Function 반환 후 step++ 하므로 step:-1 로 두면 다음 라벨의 [0] 이 실행됨.
export function gotoNextScene () {
	const llm = monogatari.storage ('llm') || {};
	const game = monogatari.storage ('game') || {};
	const next = llm.next_scene_id || '';
	monogatari.storage ({
		llm: Object.assign ({}, llm, { next_scene_id: '', prev_scene_id: '' })
	});
	if (next) {
		const isEnding = /^SCENE_ENDING_/.test (next);
		monogatari.storage ({
			game: Object.assign ({}, game, {
				current_scene_id: next
			})
		});
		if (isEnding) {
			monogatari.state ({ label: 'LLMEnd', step: -1 });
			return true;
		}
		const arr = (typeof monogatari.label === 'function' ? monogatari.label (next) : null);
		if (Array.isArray (arr)) {
			monogatari.state ({ label: next, step: -1 });
			return true;
		}
	}
	// 폴백: next_scene_id 가 없거나 라벨이 없으면 채팅으로 복귀.
	monogatari.state ({ label: 'LLMChat', step: -1 });
	return true;
}
