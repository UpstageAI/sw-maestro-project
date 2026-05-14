import { monogatari } from './engine.js';
import {
	SAVE_SLOT_PREFIX,
	SAVE_SLOT_ID,
	SAVE_SLOT_KEY,
	SAVE_SLOT_NAME,
	RESUME_SLOT_SAVE_DELAY_MS
} from './constants.js';

let _resumeSlotSaveTimer = null;
let _savingResumeSlot = false;
let _scriptAutoSaveInstalled = false;

export async function hasLocalAutoSave () {
	try {
		const data = await monogatari.Storage.get (SAVE_SLOT_KEY);
		if (!data) return false;
		if (data.game && data.game.state && data.game.state.label) return true;
		if (data.Engine && data.Engine.Label) return true;
		return false;
	} catch (e) {
		return false;
	}
}

export async function saveResumeSlot (reason = 'manual') {
	if (_savingResumeSlot) return;
	_savingResumeSlot = true;
	try {
		const label = monogatari.state ('label') || '(none)';
		const step = monogatari.state ('step');
		const sceneAtSave = monogatari.state ('scene') || '(none)';
		console.debug ('[auto-save]', SAVE_SLOT_KEY, '| label:', label, '| step:', step, '| scene:', sceneAtSave, '| reason:', reason);
		await monogatari.saveTo (SAVE_SLOT_PREFIX, SAVE_SLOT_ID, SAVE_SLOT_NAME);
	} catch (e) {
		console.warn ('[save] auto-save 실패:', e);
	} finally {
		_savingResumeSlot = false;
	}
}

export function shouldAutoSaveScriptState () {
	return monogatari.global ('playing') === true;
}

export function cancelPendingAutoSave () {
	if (_resumeSlotSaveTimer) {
		clearTimeout (_resumeSlotSaveTimer);
		_resumeSlotSaveTimer = null;
	}
}

function _scheduleScriptAutoSave (reason = 'script-state') {
	if (!shouldAutoSaveScriptState ()) return;
	if (_resumeSlotSaveTimer) clearTimeout (_resumeSlotSaveTimer);
	_resumeSlotSaveTimer = setTimeout (() => {
		_resumeSlotSaveTimer = null;
		if (shouldAutoSaveScriptState ()) saveResumeSlot (reason);
	}, RESUME_SLOT_SAVE_DELAY_MS);
}

// 디바운스를 거치지 않고 즉시 1회 저장. (beforeunload 처럼 await 불가 경로에서도
// LocalStorage setItem 이 동기이므로 resolve 전에 데이터가 localStorage 에 반영됨.)
export function flushResumeSlotSave (reason = 'flush') {
	cancelPendingAutoSave ();
	if (shouldAutoSaveScriptState ()) return saveResumeSlot (reason);
	return Promise.resolve ();
}

export function installScriptAutoSaveHook () {
	if (_scriptAutoSaveInstalled) return;
	const target = document.querySelector ('visual-novel');
	if (!target) {
		setTimeout (installScriptAutoSaveHook, 100);
		return;
	}
	_scriptAutoSaveInstalled = true;
	target.addEventListener ('didUpdateState', () => {
		_scheduleScriptAutoSave ('script-state');
	});
	window.addEventListener ('beforeunload', () => flushResumeSlotSave ('beforeunload'));
}
