import { installScriptAutoSaveHook } from './save.js';
import { cleanupCustomUI } from './game-flow.js';
import { refreshSomaMainMenu } from './menu.js';

function _syncDistractionFree () {
	const monogatari = window.Monogatari?.default;
	const isHidden = !!(monogatari?.global?.('distraction_free'));
	if (document.body) document.body.classList.toggle ('distraction-free', isHidden);
}

function _installLifecycleHooks () {
	if (!document.body) return;
	installScriptAutoSaveHook ();

	// soma:refresh-menu 커스텀 이벤트 — game-flow 가 순환 dep 없이 menu 갱신 요청할 때 사용.
	document.addEventListener ('soma:refresh-menu', () => refreshSomaMainMenu ());

	document.addEventListener ('click', (e) => {
		if (e.target?.closest?.('[data-action="distraction-free"]')) {
			setTimeout (_syncDistractionFree, 0);
		}
	});
	document.addEventListener ('keydown', (e) => {
		if (e.key === 'h' || e.key === 'H') {
			if (e.target?.matches?.('input, textarea, select')) return;
			setTimeout (_syncDistractionFree, 0);
		}
	});

	if (typeof MutationObserver === 'undefined') return;
	let _mainScreenWasVisible = false;
	const observer = new MutationObserver (() => {
		const mainScreen = document.querySelector ('[data-screen="main"]');
		const gameScreen = document.querySelector ('[data-screen="game"]');
		if (!mainScreen || !gameScreen) return;
		const mainVisible = mainScreen.offsetParent !== null;
		const gameVisible = gameScreen.offsetParent !== null;
		if (mainVisible && !gameVisible && document.body.classList.contains ('game-active')) {
			cleanupCustomUI ();
		}
		if (mainVisible && !_mainScreenWasVisible) {
			refreshSomaMainMenu ();
		}
		_mainScreenWasVisible = mainVisible;
	});
	observer.observe (document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'open', 'data-screen'] });

	const mainScreenEl = document.querySelector ('[data-screen="main"]');
	if (mainScreenEl) {
		let wasActive = mainScreenEl.classList.contains ('active');
		const focusedObs = new MutationObserver (() => {
			const isActive = mainScreenEl.classList.contains ('active');
			if (isActive && !wasActive) refreshSomaMainMenu ();
			wasActive = isActive;
		});
		focusedObs.observe (mainScreenEl, { attributes: true, attributeFilter: ['class'] });
	}
}

if (document.readyState === 'loading') {
	document.addEventListener ('DOMContentLoaded', _installLifecycleHooks, { once: true });
} else {
	_installLifecycleHooks ();
}

// textarea Enter → submit (LLM 입력창)
document.addEventListener ('keydown', function (e) {
	if (!e.target.matches?.('.llm-input textarea')) return;
	if (e.key !== 'Enter' || e.shiftKey) return;
	if (e.isComposing || e.keyCode === 229) return;
	e.preventDefault ();
	const form = e.target.closest ('text-input');
	if (form) {
		const btn = form.querySelector ('button');
		if (btn) btn.click ();
	}
});
