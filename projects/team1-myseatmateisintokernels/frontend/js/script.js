import { monogatari } from './engine.js';
import { gotoNextScene, findJumpLLMChatStep } from './scene-router.js';
import {
	showIntroLogo,
	updateSeraSprite,
	resetSeraSprite,
	showThinkingDots,
	hideThinkingDots,
	flashAffinityVignette,
	showEventToast,
	clearSuggestions,
	ensureHUD,
	updateHUD,
	hideHUD,
	pushDialogLog,
	pushRecentMessagesToDialogLog,
	clearDialogLogDom,
	ensureLogButton,
	typewriteAndAwait
} from './ui.js';
import { bootstrapSessionOnce, fetchEndingContent } from './api.js';
import { setGameActive, chatStreamState } from './game-flow.js';
import { API_BASE, SCENE_BG_KEY, CHAT_RESUME_LABELS, escapeDialogText } from './constants.js';

// ─── Monogatari 등록 ───────────────────────────────────────────────────────────

monogatari.action ('message').messages ({
	'Help': {
		title: 'Help',
		subtitle: 'Some useful Links',
		body: `
			<p><a href='https://developers.monogatari.io/documentation/'>Documentation</a> - Everything you need to know.</p>
			<p><a href='https://monogatari.io/demo/'>Demo</a> - A simple Demo.</p>
		`
	}
});

monogatari.action ('notification').notifications ({
	'Welcome': {
		title: 'Welcome',
		body: 'This is the Monogatari VN Engine',
		icon: ''
	}
});

monogatari.assets ('images', {
	'sera_first': '이세라 첫등장.png'
});

monogatari.assets ('scenes', {
	'blank_white':     'blank_white.svg',
	'fade_black':      'fade_black.svg',
	'bedroom_dawn':    'bedroom_dawn.svg',
	'apartment_door':  'apartment_door.svg',
	'train_interior':  'metro.png',
	'posttower_lobby': 'center_1floor.png',
	'elevator_panel':  'elevator_panel.svg',
	'center_hall':     'entrance.png',
	's1_room':         'entrance.png',

	// === SceneId 기반 플레이스홀더 배경 (§1.4.2) ===
	'scene_project_plan_evaluation': 'scene_project_plan_evaluation.svg',
	'scene_launch_ceremony':         'scene_launch_ceremony.svg',
	'scene_mid_evaluation':          'scene_mid_evaluation.svg',
	'scene_deep_dev':                'scene_deep_dev.svg',
	'scene_final_evaluation':        'scene_final_evaluation.svg',
	'scene_graduation_busan':        'scene_graduation_busan.svg',
	'scene_ending_instant_bad':       'scene_ending_instant_bad.svg',
	'scene_ending_bad':               'scene_ending_bad.svg',
	'scene_ending_normal_no_contact': 'scene_ending_normal_no_contact.svg',
	'scene_ending_normal_contact':    'scene_ending_normal_contact.svg',
	'scene_ending_happy':             'scene_ending_happy.svg',
	'scene_ending_marriage':          'scene_ending_marriage.svg'
});

monogatari.characters ({
	'p': {
		name: '{{player.name}}',
		color: '#8ad8ff'
	},
	'y': {
		name: '{{sera.name}}',
		color: '#ffb7d8',
		directory: '이세라_표정/이세라_표정',
		sprites: {
			calm: '평온.png',
			happy: '행복.png',
			shy: '수줍음.png',
			sad: '슬픔.png',
			angry: '화남.png',
			disgust: '혐오.png',
			excited: '흥분(좋은의미).png'
		}
	}
});

monogatari.translation ('English', {
	'보내기': '보내기',
	'↑': '↑'
});

// ─── 시나리오 라벨 ──────────────────────────────────────────────────────────────

monogatari.script ({
	'Start': [
		function () { setGameActive (true); return true; },
		// 인트로 직전 — blank_white SVG 로 즉시 흰 배경.
		'show scene blank_white',
		// 인트로 로고 오버레이.
		async function () {
			await showIntroLogo ();
			return true;
		},
		// 인트로 끝나면 검은 배경으로 페이드.
		'show scene fade_black with fadeIn',
		'jump NewGame'
	],

	'NewGame': [
		// === 씬 1: 이름 입력 ===
		{
			'Input': {
				'Text': '당신의 이름을 알려주세요.',
				'Validation': function (input) {
					return /^([가-힣]{2,6}|[A-Za-z]{2,12})$/.test (input.trim ());
				},
				'Save': function (input) {
					this.storage ({
						player: {
							name: input.trim ()
						}
					});
					return true;
				},
				'Revert': function () {
					this.storage ({
						player: {
							name: '???'
						}
					});
				},
				'Warning': '한글 2~6자 또는 영문 2~12자로 입력해 주세요.'
			}
		},

		// === 씬 2: 아침 기상 ===
		'show scene bedroom_dawn with fadeIn',
		'4월 13일, 월요일. 화창한 아침.',
		'또로로롱~ 오니쨩~! 일어날 시간이에요!!',
		'또로로롱~ 오니쨩~! 일어날 시간이에요!!',
		'…뚝.',
		'p 으… 아침인가… 벌써 시간이…',
		'p 일어나서 씻어야지…',
		'저벅… 저벅… 툭. 샤아아아아—',
		'…툭. 위이이이잉… 딸깍. 툭.',
		'p 하아… 이제야 좀 상쾌하네. 오늘은 처음 센터에 가는 날이니까 빨리 준비해야지.',

		// === 씬 3: 출근길 ===
		'show scene apartment_door with fadeIn',
		'철컥— 현관문이 닫힌다.',

		'show scene train_interior with fadeIn',
		'쿠구구궁… 덜컹… 덜컹…',
		'p 이건 탈 때마다 왜 이리 시끄러워…',
		'끼이이익… 덜컹… 슈우우우욱.',

		// === 씬 4: 포스트타워 진입 ===
		'show scene posttower_lobby with fadeIn',
		'저벅… 저벅…',
		'p 오, 여기가 소마 건물이구나. 7층이었지, 아마?',

		'show scene elevator_panel with fadeIn',
		'7층 버튼을 누른다.',
		'띵— 문이 열린다.',

		// === 씬 5: 7층 센터 홀 ===
		'show scene center_hall with fadeIn',
		'p 오오! 이곳이 센터구나. 안이 생각보다 훨씬 깔끔한걸?',
		'운 좋게 소프트웨어 마에스트로에 합격한 나는, 워크숍이 끝나고 처음으로 센터에 발을 들였다.',
		'p 센터 오픈 첫날이라 그런지 사람이 꽤 많네…! 워크숍 때는 제대로 얘기를 못해봤지만… 오늘은 꼭 팀원을 구해야지!',
		'p 워크숍 때 봤던 그녀도 있을까…? 꼭 다시 만나보고 싶어.',
		'지난주 워크숍에서 간식을 너무 많이 먹은 탓에 혈당 스파이크가 왔고, 결국 중간에 골아 떨어지는 바람에 네트워킹을 제대로 못했다. 정확히는 18번 테이블의 초코파이 20개가 원흉이었다.',
		'p 앞으로 간식은 자제하자…',
		'안쪽으로 발걸음을 옮긴다.',
		'p 이야, 벌써 서로 안면을 텄구나. 나도 워크숍 때 좀 잘할걸 그랬네…',
		'p 아니야, 지금도 늦지 않았어. 열심히 네트워킹하자!',

		// === 씬 6: S1 룸 첫 조우 ===
		'show scene s1_room with fadeIn',
		'— S1 룸 —',
		'p 아, 여기가 그곳이구나! 내가 면접 봤던 곳… 그땐 좁아 보였는데, 벽을 치우니까 엄청 넓네.',
		'저벅… 저벅… 툭.',
		'p 어?',
		'p 어..? 어…???? 아닛, 저 사람은…?',

		'show image sera_first with fadeIn',
		'창가 앞, 화사한 햇볕이 내리쬐는 자리. 신비로운 분위기의 소녀가 앉아 있었다.',
		'천사의 날개 같은 흰 머리, 사람을 홀리는 듯한 파란 눈, 가녀린 속눈썹, 보호본능을 자극하는 가녀린 체구. 그야말로 나의 이상향과 같은 존재였다.',
		'그녀의 노트북 화면엔 검은 터미널 위로 GDB 프롬프트가 깜빡이고, 옆에는 다 식어버린 아메리카노가 놓여 있었다.',
		'hide image sera_first with fadeOut',
		'jump SCENE_FIRST_MEET'
	],

	// === 소마 일정 씬 (§1.4.2 SceneId) ===
	// 구조: [<프롤로그>, 'jump LLMChat', <에필로그>, gotoNextScene]

	'SCENE_FIRST_MEET': [
		'show character y calm with fadeIn',
		'p 그때 워크숍 때 봤던 사람이잖아…? 다시 봐도 정말 눈에 띄네.',
		'p 그때 잠깐 이야기 듣다 보니 관심사가 나랑 비슷한 것 같았어. 지금이라도 한 번 말을 걸어봐야겠다…!',
		'그녀 앞으로 조심스럽게 다가간다.',
		'p 저… 저기요…!',
		'y …?',
		'p 그… 저… 혹시… 저, 기억하시나요…?',
		'y 응? 아니아니, 누구신데요?',
		'그녀가 잠시 나를 바라보더니, 뭔가 떠오른 듯 눈이 살짝 커졌다.',
		'show character y happy',
		'y 아…! 그때 워크숍 18번 테이블에서 초코파이 드시던 분이세요?',
		'p 네…! 기억해주셨군요!! 저, {{player.name}}이에요.',
		{
			'Function': {
				'Apply': function () {
					this.storage ({ sera: { name: '이세라' } });
					return true;
				},
				'Revert': function () {
					this.storage ({ sera: { name: '???' } });
					return true;
				}
			}
		},
		'y 오, 그분이셨구나? 안녕하세요. 저는 이세라라고 해요.',
		'show character y calm',
		'y 잘 부탁드려요, {{player.name}}씨.',
		'p 반갑습니다…!',
		'p (어색한 첫 인사는 끝났다. 이제 뭐라고 말을 꺼내지…)',
		'jump LLMChat',
		// === 에필로그 ===
		'show character y happy',
		'어색하면서도 즐거웠던 첫 대화. 우리는 어쩌다 같은 팀이 되기로 했다.',
		'y 그럼… 우리 같이 잘 해봐요!',
		'p 네! 잘 부탁드려요.',
		gotoNextScene
	],

	'SCENE_PROJECT_PLAN_EVALUATION': [
		'show scene scene_project_plan_evaluation with fadeIn',
		'show character y calm with fadeIn',
		'며칠 후, 첫 번째 관문인 기획 심의 날이 다가왔다.',
		'p 드디어 발표 날이네… 잘할 수 있을까?',
		'y 긴장돼요? 우리 충분히 준비했으니까 괜찮을 거예요.',
		'jump LLMChat',
		// === 에필로그 ===
		'show character y happy',
		'무사히 기획 심의를 마치고, 우리는 다음 일정으로 향했다.',
		'y 휴~ 무사히 끝났네요. 수고하셨어요!',
		'p 다행이다… 이제 발대식이지?',
		gotoNextScene
	],

	'SCENE_LAUNCH_CEREMONY': [
		'show scene scene_launch_ceremony with fadeIn',
		'show character y shy with fadeIn',
		'정장 차림의 사람들로 가득 찬 회장. 발대식이 시작되려 한다.',
		'p 이렇게 사람이 많을 줄이야…',
		'y 우와… 진짜 정식으로 시작되는 느낌이네요.',
		'jump LLMChat',
		'show character y excited',
		'발대식이 끝나고, 우리는 본격적인 개발 모드로 들어갔다.',
		'y 자! 이제부터 진짜 시작이에요!',
		'p 응! 열심히 하자.',
		gotoNextScene
	],

	'SCENE_MID_EVALUATION': [
		'show scene scene_mid_evaluation with fadeIn',
		'show character y calm with fadeIn',
		'어느새 중간 평가가 다가왔다.',
		'p 벌써 중간 평가네… 시간 진짜 빠르다.',
		'y 그러게요… 잘 해봐요, 우리.',
		'jump LLMChat',
		'show character y sad',
		'길고 긴 중간 평가가 끝났다.',
		'y 후… 멘토님들 질문이 진짜 매서웠네요.',
		'p 그래도 잘 막아낸 것 같아.',
		gotoNextScene
	],

	'SCENE_DEEP_DEV': [
		'show scene scene_deep_dev with fadeIn',
		'show character y shy with fadeIn',
		'마감이 다가오자 우리는 센터에서 밤을 새기로 했다.',
		'y 새벽까지 코딩이라니… 좀 떨려요.',
		'p 카페인 챙겨왔어. 같이 끝내자!',
		'jump LLMChat',
		'show character y happy',
		'동이 트는 창밖을 바라보며, 우리는 마지막 커밋을 푸시했다.',
		'y 우리… 진짜 해냈네요…',
		'p 응. 같이라서 가능했어.',
		gotoNextScene
	],

	'SCENE_FINAL_EVALUATION': [
		'show scene scene_final_evaluation with fadeIn',
		'show character y calm with fadeIn',
		'마지막 발표의 날. 모두의 시선이 우리에게 모였다.',
		'p 여기까지 왔구나… 잘하자!',
		'y 우리가 만든 거, 그대로 보여주기만 하면 돼요.',
		'jump LLMChat',
		'show character y excited',
		'박수 소리와 함께 발표가 끝났다.',
		'y 진짜 끝났다… 믿기지 않아요.',
		'p 수고했어. 정말 수고했어.',
		gotoNextScene
	],

	'SCENE_GRADUATION_BUSAN': [
		'show scene scene_graduation_busan with fadeIn',
		'show character y calm with fadeIn',
		'부산행 KTX. 차창 밖으로 흘러가는 풍경이 어쩐지 아쉽다.',
		'y 부산이라니… 진짜 마지막 같아요.',
		'p 그러게… 1년이 진짜 빨리 갔다.',
		'jump LLMChat',
		'show character y shy',
		'수료식이 끝나고, 우리는 광안리 바닷가에 섰다.',
		'y {{player.name}}씨… 그동안 정말 즐거웠어요.',
		gotoNextScene
	],

	// 씬 전환 디스패처 — LLMChat Conditional 의 'transition' 분기에서 진입.
	'_TransitionDispatch': [
		function () {
			const llm = monogatari.storage ('llm') || {};
			const prev = llm.prev_scene_id || '';
			const jumpIdx = findJumpLLMChatStep (prev);
			if (jumpIdx >= 0) {
				monogatari.state ({ label: prev, step: jumpIdx });
				return true;
			}
			return gotoNextScene ();
		}
	],

	'LLMChat': [
		async function () {
			const boot = this.storage ('boot') || {};
			const game = this.storage ('game') || {};
			const playerName = (this.storage ('player') || {}).name || '플레이어';

			setGameActive (true);
			// resume 경로는 handleResume 이 setSessionBootstrapped() 로 마킹 → bootstrap 스킵.
			if (boot.mode !== 'resume' && boot.mode !== 'loaded-slot') {
				await bootstrapSessionOnce (playerName);
			}
			ensureHUD ();
			updateHUD ({
				progress: typeof game.progress === 'number' ? game.progress : 0,
				affinity: typeof game.affinity === 'number' ? game.affinity : 0
			});
			resetSeraSprite ();
			ensureLogButton ();

			if (boot.mode === 'resume' || boot.mode === 'loaded-slot') {
				const recent = Array.isArray (boot.recent_messages) ? boot.recent_messages : [];
				console.debug ('[resume] restoring dialog log from BE recent_messages:', recent.length, 'entries');
				clearDialogLogDom ();
				if (recent.length > 0) {
					pushRecentMessagesToDialogLog (recent, playerName);
				}
				const sayEl = document.querySelector ('[data-ui="say"]');
				const whoEl = document.querySelector ('[data-ui="who"]');
				if (sayEl) sayEl.innerHTML = '';
				if (whoEl) whoEl.textContent = '';
				// 저장된 마지막 감정에 맞는 스프라이트 복원.
				const llmStorage = this.storage ('llm') || {};
				if (llmStorage.emotion) updateSeraSprite (llmStorage.emotion);
				this.storage ({ boot: Object.assign ({}, boot, { mode: boot.mode + '-played' }) });
			}
			clearSuggestions ();

			const prevLLM = this.storage ('llm') || {};
			this.storage ({
				llm: Object.assign ({}, prevLLM, {
					prompt: '',
					response: '',
					event_id: ''
				})
			});
			monogatari.state ({ label: 'LLMChat', step: 0 });
			return true;
		},

		{
			'Input': {
				'Text': '',
				'Type': 'textarea',
				'Class': 'llm-input',
				'Attributes': {
					'rows': '1',
					'maxlength': '300',
					'placeholder': '이세라에게 말을 걸어보세요…'
				},
				'Validation': function (input) {
					const trimmed = input.trim ();
					return trimmed.length >= 1 && trimmed.length <= 300;
				},
				'Save': function (input) {
					const prompt = input.trim ();
					const prevLLM = this.storage ('llm') || {};
					this.storage ({
						llm: Object.assign ({}, prevLLM, {
							prompt: escapeDialogText (prompt),
							response: '',
							emotion: 'NEUTRAL',
							event_id: '',
							next_scene_id: '',
							prev_scene_id: ''
						})
					});

					chatStreamState.pending = fetch (`${API_BASE}/chat`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							'Accept': 'text/event-stream'
						},
						credentials: 'include',
						body: JSON.stringify ({ message: prompt })
					});

					clearSuggestions ();
					return true;
				},
				'Revert': function () {
					const prevLLM = this.storage ('llm') || {};
					this.storage ({
						llm: Object.assign ({}, prevLLM, {
							prompt: '',
							response: '',
							emotion: 'NEUTRAL',
							event_id: ''
						})
					});
				},
				'Warning': '1자 이상 300자 이하로 입력해 주세요.',
				'actionString': '↑'
			}
		},

		'p {{llm.prompt}}',

		async function () {
			const sayEl = document.querySelector ('[data-ui="say"]');
			const whoEl = document.querySelector ('[data-ui="who"]');
			if (whoEl) whoEl.textContent = '이세라';
			if (!chatStreamState.pending) {
				console.warn ('[chat] skipped stale chat step without a pending stream');
				const prevLLM = this.storage ('llm') || {};
				this.storage ({
					llm: Object.assign ({}, prevLLM, {
						prompt: '',
						response: '',
						event_id: ''
					})
				});
				return true;
			}
			showThinkingDots ();

			let textBuffer = '';
			let streamComplete = false;
			let metaArrived = false;
			let nextSceneId = null;
			let triggeredEventId = null;
			let lastState = null;

			const handleSseEvent = (event, payload) => {
				const evtKey = String (event || '').toLowerCase ();
				switch (evtKey) {
					case 'meta':
						if (payload?.emotion) updateSeraSprite (payload.emotion);
						metaArrived = true;
						hideThinkingDots ();
						break;
					case 'delta':
					case 'message':
						if (typeof payload?.text === 'string') textBuffer += payload.text;
						else if (typeof payload?.chunk === 'string') textBuffer += payload.chunk;
						else if (typeof payload?.content === 'string') textBuffer += payload.content;
						else if (typeof payload?.delta === 'string') textBuffer += payload.delta;
						break;
					case 'state':
						lastState = payload || {};
						if (lastState.emotion) updateSeraSprite (lastState.emotion);
						flashAffinityVignette (typeof lastState.affinity_delta === 'number' ? lastState.affinity_delta : 0);
						updateHUD ({
							progress: typeof lastState.progress === 'number' ? lastState.progress : undefined,
							affinity: typeof lastState.affinity === 'number' ? lastState.affinity : undefined
						});
						break;
					case 'event_trigger':
						triggeredEventId = payload?.event_id || null;
						if (triggeredEventId) showEventToast (triggeredEventId);
						break;
					case 'scene_transition':
						nextSceneId = payload?.next_scene_id || null;
						console.log ('[SSE scene_transition]', JSON.stringify (payload));
						break;
					case 'error':
						if (!textBuffer) {
							textBuffer = '지금은 연결이 좀 불안정한 것 같아요. 잠시 후에 다시 말을 걸어주실래요?';
						}
						break;
					default:
						console.warn ('[chat] 처리되지 않은 SSE 이벤트:', event, payload);
				}
			};

			const parseSseBlock = (block, doneRef) => {
				let evt = 'message';
				let dataStr = '';
				for (const rawLine of block.split (/\r?\n/)) {
					const line = rawLine;
					if (line.startsWith ('event:')) evt = line.slice (6).trim ();
					else if (line.startsWith ('data:')) {
						const part = line.slice (5).replace (/^\s/, '');
						dataStr += (dataStr ? '\n' : '') + part;
					}
				}
				if (evt === 'end') { doneRef.done = true; return; }
				if (!dataStr) return;
				let payload;
				try { payload = JSON.parse (dataStr); }
				catch (e) {
					console.warn ('[chat] SSE data JSON parse 실패:', dataStr.slice (0, 200));
					return;
				}
				handleSseEvent (evt, payload);
			};

			try {
				const response = await chatStreamState.pending;
				chatStreamState.pending = null;
				if (!response.ok) throw new Error (`HTTP ${response.status}`);

				const reader = response.body.getReader ();
				const decoder = new TextDecoder ();

				(async () => {
					try {
						let buf = '';
						const doneRef = { done: false };
						let processedAny = false;
						while (!doneRef.done) {
							const { done: d, value } = await reader.read ();
							if (d) break;
							buf += decoder.decode (value, { stream: true });
							const blocks = buf.split (/\r?\n\r?\n/);
							buf = blocks.pop () || '';
							for (const block of blocks) {
								if (!block.trim ()) continue;
								parseSseBlock (block, doneRef);
								processedAny = true;
								if (doneRef.done) break;
							}
						}
						buf += decoder.decode ();
						if (buf.trim ()) {
							for (const block of buf.split (/\r?\n\r?\n/)) {
								if (!block.trim ()) continue;
								parseSseBlock (block, doneRef);
								processedAny = true;
							}
						}
					} catch (e) {
						console.error ('[chat] stream read error:', e);
					}
					streamComplete = true;
				}) ();
			} catch (error) {
				console.error ('[chat] fetch failed:', error);
				textBuffer = '지금은 연결이 좀 불안정한 것 같아요. 잠시 후에 다시 말을 걸어주실래요?';
				streamComplete = true;
			}

			while (!metaArrived && !streamComplete && textBuffer.length === 0) {
				await new Promise (r => setTimeout (r, 50));
			}
			hideThinkingDots ();
			sayEl.innerHTML = '';

			const PAGE_BREAK_THRESHOLD = 80;
			let typed = 0;
			let pageText = '';
			let skipToBreak = false;

			let pageState = 'typing';
			let resolveAdvance = null;

			const handleInteract = (e) => {
				if (e.type === 'keydown') {
					if (e.isComposing || e.keyCode === 229) return;
					if (!['Enter', ' ', 'ArrowRight'].includes (e.key)) return;
				}
				if (e.type === 'click' && e.target?.closest?.('text-input, button, select, input, textarea, .llm-suggestions')) return;
				if (e.type === 'keydown') e.preventDefault ();
				if (pageState === 'typing') {
					skipToBreak = true;
				} else if (pageState === 'waiting' && resolveAdvance) {
					resolveAdvance ();
					resolveAdvance = null;
				}
			};
			document.addEventListener ('click', handleInteract);
			document.addEventListener ('keydown', handleInteract);

			const waitForAdvance = () => {
				pageState = 'waiting';
				if (sayEl) sayEl.classList.add ('say--awaiting');
				return new Promise (r => { resolveAdvance = r; });
			};
			const finishWait = () => {
				if (sayEl) sayEl.classList.remove ('say--awaiting');
			};

			const skipLeadingWhitespace = () => {
				while (typed < textBuffer.length && ' \n\r\t'.includes (textBuffer[typed])) typed++;
			};

			while (typed >= textBuffer.length && !streamComplete) {
				await new Promise (r => setTimeout (r, 10));
			}
			skipLeadingWhitespace ();

			while (true) {
				if (typed >= textBuffer.length) {
					if (streamComplete) break;
					await new Promise (r => setTimeout (r, 10));
					continue;
				}

				const ch = textBuffer[typed++];
				pageText += ch;
				sayEl.innerHTML = escapeDialogText (pageText);

				let dwell = 0;
				if (/[.!?。！？]/.test (ch)) dwell = 70;
				else if (ch === '…' || ch === '⋯') dwell = 180;
				else if (/[,、]/.test (ch)) dwell = 35;

				if (/[.!?。！？]/.test (ch) && pageText.length >= PAGE_BREAK_THRESHOLD) {
					if (typed >= textBuffer.length && !streamComplete) {
						await new Promise (r => setTimeout (r, 50));
					}
					const next = textBuffer[typed];
					if (!next || next === ' ' || next === '\n') {
						await waitForAdvance ();
						finishWait ();
						skipToBreak = false;
						pageState = 'typing';
						pageText = '';
						sayEl.innerHTML = '';
						skipLeadingWhitespace ();
					}
				}

				if (!skipToBreak) {
					await new Promise (r => setTimeout (r, 30 + dwell));
				}
			}

			if (pageText.trim ()) {
				await waitForAdvance ();
				finishWait ();
			}

			document.removeEventListener ('click', handleInteract);
			document.removeEventListener ('keydown', handleInteract);

			if (textBuffer.trim ()) {
				pushDialogLog ({
					id: 'y',
					name: '이세라',
					color: '#ffb7d8',
					dialog: escapeDialogText (textBuffer)
				});
			}

			if (lastState) {
				const prevGame = this.storage ('game') || {};
				this.storage ({
					game: {
						affinity:        typeof lastState.affinity      === 'number' ? lastState.affinity      : prevGame.affinity      || 0,
						affinity_delta:  typeof lastState.affinity_delta === 'number' ? lastState.affinity_delta : 0,
						progress:        typeof lastState.progress      === 'number' ? lastState.progress      : prevGame.progress      || 0,
						chat_count:      typeof lastState.chat_count    === 'number' ? lastState.chat_count    : prevGame.chat_count    || 0,
						current_scene_id: prevGame.current_scene_id || 'SCENE_FIRST_MEET'
					}
				});
			}

			const prevGameForLLM = this.storage ('game') || {};
			const prevSceneForTransition = nextSceneId ? (prevGameForLLM.current_scene_id || '') : '';
			this.storage ({
				llm: {
					prompt: this.storage ('llm').prompt,
					response: textBuffer,
					emotion: lastState?.emotion || 'NEUTRAL',
					event_id: triggeredEventId || '',
					next_scene_id: nextSceneId || '',
					prev_scene_id: prevSceneForTransition
				}
			});

			return true;
		},

		{
			'Conditional': {
				'Condition': function () {
					const llm = this.storage ('llm') || {};
					if (llm.next_scene_id) return 'transition';
					return 'continue';
				},
				'continue': 'jump LLMChat',
				'transition': 'jump _TransitionDispatch'
			}
		}
	],

	'LLMEnd': [
		async function () {
			clearSuggestions ();
			hideThinkingDots ();
			hideHUD ();

			const game = this.storage ('game') || {};
			const sceneId = game.current_scene_id || '';
			const bgKey = SCENE_BG_KEY[sceneId];
			if (bgKey) {
				try { await monogatari.run ('show scene ' + bgKey + ' with fadeIn', false); } catch (e) {}
			}
			const ending = await fetchEndingContent ();
			if (!ending) {
				await typewriteAndAwait ('다음에 또 이야기해요, ' + ((this.storage ('player') || {}).name || '플레이어') + '씨.', { who: '이세라' });
				return true;
			}
			if (ending.title) {
				await typewriteAndAwait (`— ${ending.title} —`, { who: '' });
			}
			if (ending.narrative) {
				const sentences = String (ending.narrative).split (/(?<=[\.\?\!。！？])\s+/);
				let buf = '';
				for (const s of sentences) {
					if ((buf + ' ' + s).trim ().length > 120 && buf) {
						await typewriteAndAwait (buf.trim (), { who: '' });
						buf = s;
					} else {
						buf = (buf ? buf + ' ' : '') + s;
					}
				}
				if (buf.trim ()) await typewriteAndAwait (buf.trim (), { who: '' });
			}
			return true;
		},
		'end'
	]
});
