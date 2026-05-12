import { monogatari } from './engine.js';
import { SAVE_SLOT_KEY, CHAT_RESUME_LABELS, API_BASE } from './constants.js';
import {
	fetchSessionMe,
	postSessionsCreate,
	fetchResume,
	resetSessionBootstrapFlag,
	setSessionBootstrapped
} from './api.js';
import {
	hideHUD,
	clearSuggestions,
	hideThinkingDots,
	closeLogViewer,
	isLogViewerOpen,
	clearDialogLogDom,
	resetSeraSprite,
	confirmReset,
	confirmQuit
} from './ui.js';
import {
	hasLocalAutoSave,
	saveResumeSlot,
	flushResumeSlotSave,
	cancelPendingAutoSave,
	shouldAutoSaveScriptState
} from './save.js';

// LLMChat 의 Input.Save 콜백에서 fetch 를 시작하고, 다음 step 의 async fn 이 await 함.
// game-flow 의 handleResume 도 null 로 리셋. mutable holder 로 모듈 간 공유.
export const chatStreamState = { pending: null };

export function setGameActive (active) {
	if (active) document.body.classList.add ('game-active');
	else document.body.classList.remove ('game-active');
}

export function cleanupCustomUI () {
	setGameActive (false);
	cancelPendingAutoSave ();
	if (shouldAutoSaveScriptState ()) saveResumeSlot ('quit');
	monogatari.global ('playing', false);
	clearSuggestions ();
	hideThinkingDots ();
	hideHUD ();
	if (isLogViewerOpen ()) closeLogViewer ();
	document.querySelectorAll ('.log-button, .event-toast, .affinity-vignette').forEach (n => n.remove ());
	document.querySelectorAll ('.main-menu-overlay, .confirm-modal').forEach (n => n.remove ());
	document.querySelectorAll ('text-input').forEach (n => n.remove ());
	const sayEl = document.querySelector ('[data-ui="say"]');
	const whoEl = document.querySelector ('[data-ui="who"]');
	if (sayEl) sayEl.innerHTML = '';
	if (whoEl) whoEl.textContent = '';
	clearDialogLogDom ();
	resetSessionBootstrapFlag ();
	resetSeraSprite ();
	const bgEl = document.querySelector ('[data-screen="game"] [data-ui="background"]');
	if (bgEl) {
		bgEl.style.backgroundImage = '';
		bgEl.style.backgroundColor = '';
		bgEl.style.opacity = '';
		bgEl.style.transition = '';
	}
	// menu.js 의 refreshSomaMainMenu 는 lifecycle 훅에서 MutationObserver 가 호출.
}

export async function engineStart () {
	try {
		monogatari.global ('playing', true);
		await monogatari.onStart ();
	} catch (e) {
		console.warn ('[engine-start] onStart 실패:', e);
	}
	document.querySelectorAll ('#monogatari [data-screen]').forEach (el => {
		if (typeof el.setState === 'function') el.setState ({ open: false });
	});
	const gameScreen = document.querySelector ('#monogatari [data-screen="game"]');
	if (gameScreen && typeof gameScreen.setState === 'function') gameScreen.setState ({ open: true });
	const labels = monogatari.label ();
	const step   = monogatari.state ('step');
	if (labels && labels[step]) {
		try { await monogatari.run (labels[step]); }
		catch (e) { console.warn ('[engine-start] run 실패:', e); }
	}
}

export async function handleNewGame () {
	console.debug ('[new-game] handleNewGame entry');
	try {
		cleanupCustomUI ();
		const me = await fetchSessionMe ();
		const beHasSession = !!(me?.has_session);
		const localHasSave = await hasLocalAutoSave ();
		if (beHasSession || localHasSave) {
			const ok = await confirmReset ();
			if (!ok) return;
		}
		try {
			const res = await postSessionsCreate (true);
			if (!res.ok) console.warn ('[new-game] /sessions 응답 비정상:', res.status);
		} catch (e) {
			console.warn ('[new-game] /sessions 호출 실패 (BE 미가용?):', e);
		}
		try { await monogatari.Storage.remove (SAVE_SLOT_KEY); } catch (e) {}
		try { await monogatari.Storage.remove ('AutoSave_1'); } catch (e) {}
		try { await monogatari.resetGame (); } catch (e) {}
		monogatari.state ({ step: 0, label: 'Start' });
		resetSessionBootstrapFlag ();
		console.debug ('[new-game] starting engine');
		await engineStart ();
	} catch (err) {
		console.error ('[new-game] unhandled error in handleNewGame:', err);
		alert ('새 게임 시작 중 오류가 발생했어요. 콘솔을 확인해주세요.\n\n' + (err?.message || err));
	}
}

// 4 시나리오:
//   (1) FE+BE: 정상. 로컬 슬롯 로드 + BE recent_messages 로 채팅 로그 복원.
//   (2) FE-only: 차선. 로컬 슬롯 로드 + BE 세션 새로 생성.
//   (3) BE-only: 이어하기 불가. BE 세션 초기화하고 alert.
//   (4) Neither: alert.
export async function handleResume () {
	console.debug ('[resume] entry');
	try {
		document.querySelectorAll ('text-input').forEach (n => n.remove ());

		const [me, localHasSave] = await Promise.all ([fetchSessionMe (), hasLocalAutoSave ()]);
		const beHasSession = !!me?.has_session;
		const beIsStarted  = beHasSession && me?.is_started !== false;
		console.debug ('[resume] hasLocal=', localHasSave, '| beHasSession=', beHasSession, '| beIsStarted=', beIsStarted, '| me=', me);

		if (!localHasSave) {
			if (beHasSession) {
				console.debug ('[resume] BE-only detected — resetting BE session');
				try { await postSessionsCreate (true); } catch (e) { console.warn ('[resume] BE reset failed:', e); }
			}
			alert ('저장된 게임이 없습니다. 새로 시작해주세요.');
			// menu.js 의 refreshSomaMainMenu 를 직접 호출하면 순환 dep → 커스텀 이벤트로 위임.
			document.dispatchEvent (new CustomEvent ('soma:refresh-menu'));
			return;
		}

		let playerName = 'Player';
		try {
			const slot = await monogatari.Storage.get (SAVE_SLOT_KEY);
			playerName = slot?.game?.storage?.player?.name || playerName;
		} catch (e) {}

		if (!beHasSession) {
			console.debug ('[resume] BE session missing — creating');
			try { await postSessionsCreate (false); } catch (e) { console.warn ('[resume] /sessions create failed:', e); }
		}
		if (!beIsStarted) {
			console.debug ('[resume] BE session not started — calling /sessions/me/start');
			try {
				await fetch (`${API_BASE}/sessions/me/start`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					credentials: 'include',
					body: JSON.stringify ({ player_name: playerName })
				});
			} catch (e) { console.warn ('[resume] /sessions/me/start failed:', e); }
		}

		let recentMessages = [];
		if (beIsStarted) {
			const r = await fetchResume ();
			if (r.ok && r.data) {
				recentMessages = Array.isArray (r.data.recent_messages) ? r.data.recent_messages : [];
				console.debug ('[resume] BE recent_messages:', recentMessages.length, 'entries');
			} else {
				console.warn ('[resume] /sessions/me/resume failed status=', r.status);
			}
		}
		setSessionBootstrapped ();

		console.debug ('[resume] loadFromSlot start | key=', SAVE_SLOT_KEY);
		try {
			await monogatari.loadFromSlot (SAVE_SLOT_KEY);
		} catch (e) {
			console.error ('[resume] loadFromSlot failed:', e);
			alert ('저장된 게임을 불러오지 못했어요.\n' + (e?.message || e));
			return;
		}
		console.debug (
			'[resume] loadFromSlot done | label=', monogatari.state ('label'),
			'| step=', monogatari.state ('step'),
			'| scene=', monogatari.state ('scene'),
			'| storage=', monogatari.storage ()
		);

		const restoredLabel = monogatari.state ('label') || 'Start';

		setGameActive (true);
		monogatari.global ('playing', true);
		chatStreamState.pending = null;
		document.querySelectorAll ('#monogatari [data-screen]').forEach (el => {
			if (typeof el.setState === 'function') el.setState ({ open: false });
		});
		const gameScreen = document.querySelector ('#monogatari [data-screen="game"]');
		if (gameScreen && typeof gameScreen.setState === 'function') gameScreen.setState ({ open: true });

		if (CHAT_RESUME_LABELS.has (restoredLabel)) {
			const prevLLM = monogatari.storage ('llm') || {};
			const prevBoot = monogatari.storage ('boot') || {};
			monogatari.storage ({
				llm: Object.assign ({}, prevLLM, {
					prompt: '',
					response: '',
					event_id: ''
				}),
				boot: Object.assign ({}, prevBoot, {
					mode: 'loaded-slot',
					recent_messages: recentMessages
				})
			});
			monogatari.state ({ label: 'LLMChat', step: 0 });
		}

		const labels = monogatari.label ();
		const stepNow = monogatari.state ('step');
		console.debug ('[resume] dispatching | label=', monogatari.state ('label'), '| step=', stepNow, '| labels.length=', labels?.length);
		if (labels && typeof labels[stepNow] !== 'undefined') {
			try { await monogatari.run (labels[stepNow]); }
			catch (e) { console.error ('[resume] run failed:', e); }
		} else {
			console.warn ('[resume] no script step at index', stepNow, '— labels=', labels);
		}
	} catch (err) {
		console.error ('[resume] unhandled error:', err);
		alert ('이어 하기 처리 중 오류가 발생했어요. 콘솔을 확인해주세요.\n\n' + (err?.message || err));
	}
}

// 우리만의 Quit 흐름 — confirm 후 await saveTo (race 차단) → engine.run('end').
export async function handleSomaQuit () {
	console.debug ('[soma-quit] entry');
	try {
		const ok = await confirmQuit ();
		if (!ok) return;
		await flushResumeSlotSave ('soma-quit');
		try { await monogatari.run ('end'); }
		catch (e) { console.warn ('[soma-quit] engine.run("end") 실패:', e); }
	} catch (err) {
		console.error ('[soma-quit] unhandled error:', err);
	}
}
