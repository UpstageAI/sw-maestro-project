import {
	escapeDialogText,
	SERA_SPRITE_MAP,
	SERA_SPRITE_FILE,
	SERA_FADE_MS,
	spriteUrl,
	EVENT_LABELS,
	finiteNumber,
	API_BASE
} from './constants.js';

// ─── 인트로 로고 ───────────────────────────────────────────────────────────────

let _introLogoEl = null;
export function showIntroLogo () {
	return new Promise (async (resolve) => {
		if (_introLogoEl) {
			_introLogoEl.remove ();
			_introLogoEl = null;
		}
		document.body.classList.add ('intro-active');
		const overlay = document.createElement ('div');
		overlay.className = 'intro-logo';
		overlay.innerHTML = `
			<div class="intro-logo__inner">
				<img src="assets/logo/game_logo.jpeg" alt="커널을 좋아하는 옆자리의 그녀" />
				<div class="intro-logo__subtitle">Software Maestro &times; First Love</div>
			</div>
		`;
		document.body.appendChild (overlay);
		_introLogoEl = overlay;

		void overlay.offsetWidth;
		overlay.classList.add ('intro-logo--visible');
		await new Promise (r => setTimeout (r, 2500));
		await new Promise (r => setTimeout (r, 2000));
		overlay.classList.add ('intro-logo--leaving');
		await new Promise (r => setTimeout (r, 1500));
		if (overlay.parentNode) overlay.parentNode.removeChild (overlay);
		_introLogoEl = null;
		document.body.classList.remove ('intro-active');
		resolve ();
	});
}

// ─── 세라 스프라이트 ───────────────────────────────────────────────────────────

let _seraCurrentSprite = null;

export function resetSeraSprite () {
	_seraCurrentSprite = null;
}

export function updateSeraSprite (emotion) {
	const spriteKey = SERA_SPRITE_MAP[emotion] || 'calm';
	const savedCharEl = document.querySelector ('[data-character="y"]');
	const domSprite = savedCharEl?.getAttribute?.('data-sprite') || null;
	if (_seraCurrentSprite === spriteKey && domSprite !== spriteKey) _seraCurrentSprite = null;
	if (_seraCurrentSprite === spriteKey) return;
	_seraCurrentSprite = spriteKey;

	const charEl = document.querySelector ('[data-character="y"]');
	if (!charEl) return;

	const url = spriteUrl (spriteKey);
	const fadeMs = SERA_FADE_MS[emotion] ?? 350;

	const newImg = document.createElement ('img');
	newImg.src = url;
	newImg.alt = 'Sera';
	newImg.className = 'sera-sprite-fade-in';
	newImg.style.transition = `opacity ${fadeMs}ms ease`;

	if (charEl.tagName === 'IMG') {
		const parent = charEl.parentElement;
		if (!parent) return;
		newImg.setAttribute ('data-character', 'y');
		newImg.setAttribute ('data-sprite', spriteKey);
		newImg.style.cssText = charEl.style.cssText + `; opacity: 0; transition: opacity ${fadeMs}ms ease`;
		newImg.className = charEl.className;
		parent.insertBefore (newImg, charEl);
		requestAnimationFrame (() => {
			newImg.style.opacity = '1';
			charEl.style.opacity = '0';
			charEl.style.transition = `opacity ${fadeMs}ms ease`;
		});
		setTimeout (() => {
			if (charEl.parentNode) charEl.parentNode.removeChild (charEl);
		}, fadeMs + 50);
	} else {
		const oldImg = charEl.querySelector ('img');
		if (oldImg) oldImg.src = url;
		charEl.setAttribute ('data-sprite', spriteKey);
	}
}

// ─── 생각 중 점 애니메이션 ──────────────────────────────────────────────────────

export function showThinkingDots () {
	const sayEl = document.querySelector ('[data-ui="say"]');
	if (!sayEl) return;
	sayEl.innerHTML = '<span class="thinking-dots" aria-label="Thinking"><i></i><i></i><i></i></span>';
}

export function hideThinkingDots () {
	const sayEl = document.querySelector ('[data-ui="say"]');
	const dots = sayEl?.querySelector ('.thinking-dots');
	if (dots) sayEl.innerHTML = '';
}

// ─── 호감도 비네트 이펙트 ──────────────────────────────────────────────────────

export function flashAffinityVignette (delta) {
	if (typeof delta !== 'number' || Math.abs (delta) < 5) return;
	const game = document.querySelector ('[data-screen="game"]') || document.body;
	const v = document.createElement ('div');
	v.className = 'affinity-vignette';
	if (delta >= 10)        v.dataset.tone = 'love';
	else if (delta >= 5)    v.dataset.tone = 'warm';
	else if (delta > -10)   v.dataset.tone = 'cool';
	else                    v.dataset.tone = 'severe';
	game.appendChild (v);
	if (delta <= -50) v.classList.add ('affinity-vignette--shake');
	requestAnimationFrame (() => v.classList.add ('affinity-vignette--visible'));
	setTimeout (() => v.classList.add ('affinity-vignette--leaving'), 600);
	setTimeout (() => { if (v.parentNode) v.parentNode.removeChild (v); }, 1300);
}

// ─── 이벤트 토스트 ─────────────────────────────────────────────────────────────

export function showEventToast (eventId) {
	const meta = EVENT_LABELS[eventId];
	if (!meta) return;
	const root = document.body;
	const toast = document.createElement ('div');
	toast.className = 'event-toast' + (meta.sign === '+' ? ' event-toast--like' : ' event-toast--dislike');
	toast.innerHTML = `<span class="event-toast__sign">${meta.sign}</span><span class="event-toast__body">${meta.text}</span>`;
	root.appendChild (toast);
	requestAnimationFrame (() => toast.classList.add ('event-toast--visible'));
	setTimeout (() => toast.classList.add ('event-toast--leaving'), 1900);
	setTimeout (() => { if (toast.parentNode) toast.parentNode.removeChild (toast); }, 2500);
}

// ─── 추천 말풍선 (Suggestions) ─────────────────────────────────────────────────

let _suggestionsStrip = null;

export async function fetchAndRenderSuggestions () {
	clearSuggestions ();
	let suggestions = [];
	try {
		const res = await fetch (`${API_BASE}/chat/suggestions`, {
			method: 'GET',
			credentials: 'include'
		});
		if (res.ok) {
			const json = await res.json ();
			suggestions = json?.data?.suggestions || [];
		}
	} catch (e) {
	}
	if (suggestions.length === 0) return;
	renderSuggestionsStrip (suggestions);
}

function renderSuggestionsStrip (suggestions) {
	const game = document.querySelector ('[data-screen="game"]') || document.body;
	const strip = document.createElement ('div');
	strip.className = 'llm-suggestions';
	strip.innerHTML = '<div class="llm-suggestions__label">💡 이렇게 말해볼까요?</div>';
	const list = document.createElement ('div');
	list.className = 'llm-suggestions__list';
	suggestions.forEach (s => {
		const chip = document.createElement ('button');
		chip.type = 'button';
		chip.className = 'llm-suggestions__chip';
		chip.textContent = s;
		chip.addEventListener ('click', (ev) => {
			ev.preventDefault ();
			ev.stopPropagation ();
			const ta = document.querySelector ('text-input.llm-input textarea');
			if (ta) {
				ta.value = s;
				ta.dispatchEvent (new Event ('input', { bubbles: true }));
				ta.focus ();
			}
		});
		list.appendChild (chip);
	});
	const refresh = document.createElement ('button');
	refresh.type = 'button';
	refresh.className = 'llm-suggestions__refresh';
	refresh.title = '추천 다시 받기';
	refresh.setAttribute ('aria-label', '추천 다시 받기');
	refresh.textContent = 'R';
	refresh.addEventListener ('click', (ev) => {
		ev.preventDefault ();
		ev.stopPropagation ();
		fetchAndRenderSuggestions ();
	});
	list.appendChild (refresh);
	strip.appendChild (list);
	game.appendChild (strip);
	_suggestionsStrip = strip;
}

export function clearSuggestions () {
	if (_suggestionsStrip && _suggestionsStrip.parentNode) {
		_suggestionsStrip.parentNode.removeChild (_suggestionsStrip);
	}
	_suggestionsStrip = null;
	document.querySelectorAll ('.llm-suggestions').forEach (n => n.remove ());
}

// ─── 타이프라이터 ─────────────────────────────────────────────────────────────

export function typewriteAndAwait (text, opts = {}) {
	const sayEl = document.querySelector ('[data-ui="say"]');
	const whoEl = document.querySelector ('[data-ui="who"]');
	if (!sayEl) return Promise.resolve ();
	if (whoEl) whoEl.textContent = opts.who || '';
	sayEl.innerHTML = '';
	sayEl.classList.remove ('say--awaiting');

	return new Promise ((resolve) => {
		let i = 0;
		let skip = false;
		const onInteract = (e) => {
			if (e.type === 'keydown') {
				if (e.isComposing || e.keyCode === 229) return;
				if (!['Enter', ' ', 'ArrowRight'].includes (e.key)) return;
				if (e.target?.matches?.('textarea, input')) return;
				e.preventDefault ();
			}
			if (e.type === 'click' && e.target?.closest?.('text-input, button, select, input, textarea, .llm-suggestions')) return;
			if (i < text.length) {
				skip = true;
			} else {
				cleanup ();
				if (!opts.silentLog) {
					pushDialogLog ({
						id: opts.id || (opts.who ? 'y' : 'narrator'),
						name: opts.who || '',
						color: opts.color || (opts.who === 'Sera' ? '#ffb7d8' : '#fff'),
						dialog: escapeDialogText (text)
					});
				}
				resolve ();
			}
		};
		const cleanup = () => {
			document.removeEventListener ('click', onInteract);
			document.removeEventListener ('keydown', onInteract);
			sayEl.classList.remove ('say--awaiting');
		};
		document.addEventListener ('click', onInteract);
		document.addEventListener ('keydown', onInteract);

		(async () => {
			while (i < text.length) {
				const ch = text[i++];
				sayEl.innerHTML = escapeDialogText (text.slice (0, i));
				let dwell = 0;
				if (/[.!?]/.test (ch)) dwell = 70;
				else if (ch === ',' || ch === ';') dwell = 180;
				else if (/[, ]/.test (ch)) dwell = 35;
				if (!skip) await new Promise (r => setTimeout (r, 30 + dwell));
			}
			sayEl.classList.add ('say--awaiting');
		}) ();
	});
}

// ─── 모달 (confirm) ─────────────────────────────────────────────────────────

function _confirmModal ({ title, body, ok = 'OK', cancel = 'Cancel' }) {
	return new Promise ((resolve) => {
		const overlay = document.createElement ('div');
		overlay.className = 'confirm-modal';
		overlay.innerHTML = `
			<div class="confirm-modal__panel" role="alertdialog">
				<div class="confirm-modal__title">${escapeDialogText (title || '')}</div>
				<div class="confirm-modal__body">${escapeDialogText (body || '')}</div>
				<div class="confirm-modal__buttons">
					<button type="button" class="confirm-modal__btn confirm-modal__btn--cancel">${escapeDialogText (cancel)}</button>
					<button type="button" class="confirm-modal__btn confirm-modal__btn--ok">${escapeDialogText (ok)}</button>
				</div>
			</div>
		`;
		document.body.appendChild (overlay);
		void overlay.offsetWidth;
		overlay.classList.add ('confirm-modal--visible');
		const close = (decision) => {
			overlay.classList.remove ('confirm-modal--visible');
			setTimeout (() => { if (overlay.parentNode) overlay.parentNode.removeChild (overlay); }, 250);
			resolve (decision);
		};
		overlay.querySelector ('.confirm-modal__btn--cancel').addEventListener ('click', () => close (false));
		overlay.querySelector ('.confirm-modal__btn--ok').addEventListener ('click', () => close (true));
	});
}

export function confirmReset () {
	return _confirmModal ({
		title:  '기존 진행을 초기화할까요?',
		body:   '현재 세션과 저장된 진행 데이터가 모두 삭제됩니다. 새로 시작하시겠어요?',
		ok:     '새로 시작',
		cancel: '취소'
	});
}

export function confirmQuit () {
	return _confirmModal ({
		title:  '메인 메뉴로 돌아갈까요?',
		body:   '현재 진행 상황은 자동으로 저장돼요. 메인 메뉴에서 다시 이어 할 수 있어요.',
		ok:     '나가기',
		cancel: '취소'
	});
}

// ─── HUD (진행도 / 호감도) ──────────────────────────────────────────────────

let _hudEl = null;
let _hudHideTimer = null;

export function ensureHUD () {
	if (_hudEl && document.body.contains (_hudEl)) {
		// hideHUD 가 leaving 클래스를 붙이고 400ms 후 DOM 제거 예약.
		// resume 이 그 사이에 일어나면 stale 요소 재사용 — leaving 클래스 제거 후 opacity 리셋.
		_hudEl.classList.remove ('hud-progress--leaving');
		_hudEl.style.opacity = '';
		return _hudEl;
	}
	const game = document.querySelector ('[data-screen="game"]') || document.body;
	const hud = document.createElement ('div');
	hud.className = 'hud-progress';
	hud.innerHTML = `
		<div class="hud-progress__row">
			<span class="hud-progress__label">진행도</span>
			<div class="hud-progress__bar"><div class="hud-progress__fill" style="width:0%"></div></div>
			<span class="hud-progress__pct">0%</span>
		</div>
		<div class="hud-progress__row hud-progress__row--aff">
			<span class="hud-progress__label">호감도</span>
			<span class="hud-progress__affinity">0</span>
		</div>
	`;
	game.appendChild (hud);
	_hudEl = hud;
	return hud;
}

export function updateHUD ({ progress, affinity }) {
	const hud = ensureHUD ();
	progress = finiteNumber (progress, undefined);
	affinity = finiteNumber (affinity, undefined);
	if (typeof progress === 'number') {
		const fill = hud.querySelector ('.hud-progress__fill');
		const pct = hud.querySelector ('.hud-progress__pct');
		const clamped = Math.max (0, Math.min (100, progress));
		if (fill) fill.style.width = clamped + '%';
		if (pct) pct.textContent = clamped + '%';
	}
	if (typeof affinity === 'number') {
		const a = hud.querySelector ('.hud-progress__affinity');
		if (a) {
			a.textContent = String (affinity);
			a.classList.remove ('hud-progress__affinity--pos', 'hud-progress__affinity--neg');
			if (affinity > 0) a.classList.add ('hud-progress__affinity--pos');
			else if (affinity < 0) a.classList.add ('hud-progress__affinity--neg');
		}
	}
}

export function hideHUD () {
	if (!_hudEl) return;
	const target = _hudEl;
	target.classList.add ('hud-progress--leaving');
	if (_hudHideTimer) clearTimeout (_hudHideTimer);
	_hudHideTimer = setTimeout (() => {
		_hudHideTimer = null;
		// resume 이 400ms 내에 일어나 ensureHUD 가 같은 요소를 되살린 경우 leaving 클래스가 이미 제거됨.
		if (target.classList.contains ('hud-progress--leaving') && target.parentNode) {
			target.parentNode.removeChild (target);
			if (_hudEl === target) _hudEl = null;
		}
	}, 400);
}

// ─── 대화 로그 ─────────────────────────────────────────────────────────────────

export function clearDialogLogDom () {
	const dlogList = document.querySelector ('[data-component="dialog-log"] [data-content="log"]');
	if (dlogList) dlogList.querySelectorAll ('[data-spoke]').forEach (n => n.remove ());
}

export function pushRecentMessagesToDialogLog (recent, playerName) {
	if (!Array.isArray (recent)) return;
	recent.forEach (m => {
		if (!m || !m.content) return;
		if (m.role === 'USER') {
			pushDialogLog ({ id: 'p', name: playerName, color: '#8ad8ff', dialog: escapeDialogText (m.content) });
		} else if (m.role === 'ASSISTANT') {
			pushDialogLog ({ id: 'y', name: 'Sera', color: '#ffb7d8', dialog: escapeDialogText (m.content) });
		} else {
			pushDialogLog ({ id: 'narrator', dialog: escapeDialogText (m.content) });
		}
	});
}

// dialog-log 컴포넌트의 write() 와 동일한 형식으로 DOM 에 직접 append.
// Component.instances 경로에서 race 로 push 가 누락되는 사례가 있어 직접 querySelector 로 대체.
export function pushDialogLog ({ id = 'narrator', name = '', color = '#fff', dialog = '' }) {
	if (!dialog) return;
	const dlogList = document.querySelector ('[data-component="dialog-log"] [data-content="log"]');
	if (!dlogList) return;
	const placeholder = dlogList.querySelector ('[data-content="placeholder"]');
	if (placeholder) placeholder.remove ();
	const safeColor = String (color).replace (/[^#a-zA-Z0-9(),. ]/g, '');
	const html = (id !== 'narrator' && id !== 'centered')
		? `<div data-spoke="${id}" class="named"><span style="color:${safeColor};">${escapeDialogText (name)} </span><p>${dialog}</p></div>`
		: `<div data-spoke="${id}" class="unnamed"><p>${dialog}</p></div>`;
	dlogList.insertAdjacentHTML ('beforeend', html);
}

export function readDialogLogEntries () {
	const logEl = document.querySelector ('[data-component="dialog-log"]');
	if (!logEl) return [];
	const entries = [];
	logEl.querySelectorAll ('[data-spoke]').forEach (entry => {
		const id = entry.getAttribute ('data-spoke') || 'narrator';
		const isNamed = entry.classList.contains ('named');
		const nameSpan = entry.querySelector ('span');
		const dialogP = entry.querySelector ('p');
		entries.push ({
			id,
			named: isNamed,
			name: isNamed && nameSpan ? nameSpan.textContent.trim () : '',
			color: isNamed && nameSpan ? (nameSpan.style.color || '') : '',
			dialog: dialogP ? dialogP.innerHTML : ''
		});
	});
	return entries;
}

// ─── 로그 뷰어 모달 ────────────────────────────────────────────────────────────

let _logViewerEl = null;

function _renderUnifiedLog (listEl, entries) {
	listEl.innerHTML = '';
	if (!entries.length) {
		listEl.innerHTML = '<div class="log-viewer__empty">아직 대화가 없어요.</div>';
		return;
	}
	const fragment = document.createDocumentFragment ();
	entries.forEach (entry => {
		const row = document.createElement ('div');
		const variant = entry.id === 'p' ? 'user'
			: entry.id === 'y' ? 'assistant'
			: 'narration';
		row.className = `log-viewer__row log-viewer__row--${variant}`;
		const label = entry.named && entry.name
			? entry.name
			: (entry.id === 'centered' ? '' : '내레이션');
		const colorStyle = entry.color ? ` style="color:${entry.color}"` : '';
		row.innerHTML = `
			<div class="log-viewer__role"${colorStyle}>${escapeDialogText (label)}</div>
			<div class="log-viewer__bubble">${entry.dialog}</div>
		`;
		fragment.appendChild (row);
	});
	listEl.appendChild (fragment);
}

export async function openLogViewer () {
	if (_logViewerEl) return;
	const overlay = document.createElement ('div');
	overlay.className = 'log-viewer';
	overlay.innerHTML = `
		<div class="log-viewer__panel" role="dialog" aria-label="대화 기록">
			<div class="log-viewer__header">
				<span class="log-viewer__title">대화 기록</span>
				<button type="button" class="log-viewer__close" aria-label="닫기">×</button>
			</div>
			<div class="log-viewer__list" tabindex="0"></div>
		</div>
	`;
	document.body.appendChild (overlay);
	_logViewerEl = overlay;
	void overlay.offsetWidth;
	overlay.classList.add ('log-viewer--visible');

	const listEl = overlay.querySelector ('.log-viewer__list');
	const closeEl = overlay.querySelector ('.log-viewer__close');

	closeEl.addEventListener ('click', closeLogViewer);
	overlay.addEventListener ('click', (e) => { if (e.target === overlay) closeLogViewer (); });

	_renderUnifiedLog (listEl, readDialogLogEntries ());
	listEl.scrollTop = listEl.scrollHeight;
}

export function closeLogViewer () {
	if (!_logViewerEl) return;
	_logViewerEl.classList.remove ('log-viewer--visible');
	const el = _logViewerEl;
	setTimeout (() => { if (el.parentNode) el.parentNode.removeChild (el); }, 250);
	_logViewerEl = null;
}

export function isLogViewerOpen () {
	return !!_logViewerEl;
}

export function ensureLogButton () {
	if (document.querySelector ('.log-button')) return;
	const game = document.querySelector ('[data-screen="game"]') || document.body;
	const btn = document.createElement ('button');
	btn.type = 'button';
	btn.className = 'log-button';
	btn.title = '대화 기록';
	btn.setAttribute ('aria-label', '대화 기록');
	btn.textContent = '📜로그';
	btn.addEventListener ('click', (e) => {
		e.preventDefault ();
		e.stopPropagation ();
		openLogViewer ();
	});
	game.appendChild (btn);
}
