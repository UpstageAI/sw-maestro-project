import type { Language, QuickOption } from './types';

type Strings = {
  title: string;
  tagline: string;
  language: string;

  /* topbar */
  resetBtn: string;
  journalBtn: string;

  /* composer */
  composerPlaceholder: string;
  send: string;

  /* mission card labels */
  estimated: string;
  minutes: string;
  proof: string;
  route: string;
  pick: string;
  swap: string;

  /* photo upload card */
  uploadLabel: string;
  uploadHint: string;
  uploadOrDrop: string;
  dropHere: string;
  selectPhoto: string;
  changePhoto: string;
  submitPhoto: string;

  /* verdict */
  pass: string;
  fail: string;

  /* greeting + ack lines */
  greet: string;
  askArea: string;
  ackArea: (area: string) => string;
  askGroup: string;
  ackGroup: string;
  askTime: string;
  ackTime: string;
  askMood: string;
  ackMood: string;
  askAvoid: string;
  ackAvoid: string;
  generating: string;
  presentMissions: string;
  ackPick: (title: string) => string;
  promptPhoto: string;
  verifying: string;
  promptNext: string;

  /* free-text fallbacks */
  fallbackUnknown: string;
  fallbackPhotoNeeded: string;
  fallbackBusy: string;
  fallbackNoMoreSwap: string;

  /* errors */
  errorPrefix: string;

  /* quick replies */
  qrSkip: string;
  qrAnyMood: string;
  qrSubmit: string;
  qrRerollAll: string;
  qrAnotherMission: string;
  qrStartOver: string;
  qrRetry: string;
  ackRetry: (title: string) => string;

  /* journal */
  journalTitle: string;
  journalEmpty: string;
  journalCount: (n: number) => string;
  clearJournal: string;
  clearConfirm: string;
  closeJournal: string;
  resetConfirm: string;

  /* mission panel */
  panelTitle: string;
  panelEmpty: string;
  panelCount: (n: number) => string;
  panelOpenMobile: string;
  panelCloseMobile: string;
  panelMissionsReady: string;
  panelLookRight: string;
  panelStateActive: string;
  panelStatePassed: string;
  panelStateFailed: string;
  panelStateRejected: string;
  panelStatePool: string;
  panelGenerateMore: string;
  panelTakeFromPool: string;
  panelChangeFromPool: string;
  panelRejectFromPool: string;
  ackChange: (title: string) => string;
  ackChangeDone: (title: string) => string;
  ackReject: (title: string) => string;

  areasUnavailable: string;

  /* quick reply option pools */
  groupOptions: QuickOption[];
  timeOptions: QuickOption[];
  moodOptions: QuickOption[];
  avoidOptions: QuickOption[];
};

export const I18N: Record<Language, Strings> = {
  ko: {
    title: '두리번',
    tagline: '지금 여기서만 가능한 즉흥 미션',
    language: '언어',

    resetBtn: '처음부터',
    journalBtn: '여행 기록',

    composerPlaceholder: '버튼으로 답해도 되고, 자유롭게 입력해도 돼...',
    send: '전송',

    estimated: '예상',
    minutes: '분',
    proof: '인증',
    route: '동선',
    pick: '이거 받기',
    swap: '바꿔',

    uploadLabel: '도착했으면 사진 한 장 올려',
    uploadHint: 'JPG / PNG · 탭해서 선택',
    uploadOrDrop: '클릭하거나 사진을 끌어다 놔도 돼',
    dropHere: '⬇ 여기에 놔 ⬇',
    selectPhoto: '📷 사진 선택',
    changePhoto: '다른 사진',
    submitPhoto: '인증 제출',

    pass: '통과!',
    fail: '음... 다시?',

    greet:
      '안녕! 두리번이야. 몇 가지만 묻고 바로 골목 퀘스트 5개 골라줄게. 부담 없이 답해.',
    askArea: '지금 어느 골목 와 있어? 👀',
    ackArea: (a) => `${a}, 좋은 동네지.`,
    askGroup: '거기 누구랑 있어?',
    ackGroup: '오케이, 메모해뒀어.',
    askTime: '얼마나 시간 있어? 미션 길이를 거기에 맞춰줄게.',
    ackTime: '시간도 챙겼어.',
    askMood: '오늘 어떤 기분으로 가볼까? 키워드 하나만 골라.',
    ackMood: '느낌 받았어.',
    askAvoid: '마지막 — 피하고 싶은 거 있어? (여러 개면 그냥 입력해도 돼)',
    ackAvoid: '알겠어. 자, 이제 골목 두리번거려볼게.',
    generating: '잠깐만, 골목 두리번거리는 중...',
    presentMissions: '자, 다음 퀘스트는 5개야. 마음에 드는 거 받아.',
    ackPick: (t) => `오, "${t}". 좋은 선택이야.`,
    promptPhoto: '도착해서 미션 인증할 준비되면 사진 한 장 올려줘.',
    verifying: '사진 살펴볼게...',
    promptNext: '다음 미션 갈래?',

    fallbackUnknown: '음, 무슨 말인지 모르겠어. 아래 버튼으로 답해줘 ㅎㅎ',
    fallbackPhotoNeeded: '미션 인증은 사진이 있어야 돼. 한 장 올려줘.',
    fallbackBusy: '잠깐만, 처리 중...',
    fallbackNoMoreSwap: '이 동네에서 새로 줄 수 있는 미션이 더 없어. 일단 이 미션은 돌려둘게.',

    errorPrefix: '오류',

    qrSkip: '건너뛸래',
    qrAnyMood: '🎲 아무거나',
    qrSubmit: '인증 제출',
    qrRerollAll: '🔄 전부 다시',
    qrAnotherMission: '✨ 다른 미션',
    qrStartOver: '🏠 처음부터',
    qrRetry: '🔄 다시 시도',
    ackRetry: (t) => `오, "${t}" 다시 도전이지. 한 번 더 가보자.`,

    journalTitle: '여행 기록',
    journalEmpty: '아직 기록된 미션이 없어. 한 번 도전해봐!',
    journalCount: (n) => `${n}건의 미션 기록`,
    clearJournal: '전체 삭제',
    clearConfirm: '정말 다 지울까? 되돌릴 수 없어.',
    closeJournal: '닫기',
    resetConfirm: '대화 처음부터 시작할까? 지금 진행 중인 미션은 사라져.',

    panelTitle: '미션함',
    panelEmpty: '미션이 여기 쌓일 거야.\n봇한테 답하면 5개 골라줄게.',
    panelCount: (n) => `${n}개`,
    panelOpenMobile: '미션함 열기',
    panelCloseMobile: '닫기',
    panelMissionsReady: '미션 5개 준비했어.',
    panelLookRight: '오른쪽 미션함에서 골라봐 →',
    panelStateActive: '진행 중',
    panelStatePassed: '통과',
    panelStateFailed: '실패',
    panelStateRejected: '거절',
    panelStatePool: '대기',
    panelGenerateMore: '✨ 새로 5개 가져와',
    panelTakeFromPool: '받기',
    panelChangeFromPool: '바꿔',
    panelRejectFromPool: '거절',
    ackChange: (title) => `오케이, "${title}" 같은 장소로 다른 미션 줄게.`,
    ackChangeDone: (title) => `자, "${title}" — 이건 어때?`,
    ackReject: (title) => `오케이, "${title}"는 빼둘게.`,

    areasUnavailable: '동네 정보를 못 받아왔어. 백엔드가 켜져 있는지 확인해줘.',

    groupOptions: [
      { label: '🧍 혼자', payload: '혼자' },
      { label: '💕 커플', payload: '커플' },
      { label: '🤝 친구 둘', payload: '친구 2명' },
      { label: '🍻 친구 셋', payload: '친구 3명' },
      { label: '🎉 친구 넷+', payload: '친구 4명+' }
    ],
    timeOptions: [
      { label: '⚡ 30분만 (짧게)', payload: '30분 정도' },
      { label: '🍵 1~2시간 (커피 한 잔 텀)', payload: '1~2시간' },
      { label: '🌳 반나절 (천천히)', payload: '반나절' },
      { label: '🌙 저녁까지 (밤까지 놀래)', payload: '하루 종일' }
    ],
    moodOptions: [
      { label: '💭 감성 한 모금', payload: '감성적인 분위기' },
      { label: '🔥 도전적인 거', payload: '도전적인 미션' },
      { label: '🌿 조용히 힐링', payload: '조용한 힐링' },
      { label: '🤣 빵 터지게', payload: '웃기고 가벼운 분위기' },
      { label: '🤝 진짜 로컬', payload: '깊은 로컬 경험' },
      { label: '📷 인생샷 건지자', payload: '사진 잘 나오는 곳' }
    ],
    avoidOptions: [
      { label: '🌶 매운 거', payload: '매운 음식' },
      { label: '🍷 술', payload: '음주' },
      { label: '🐟 해산물', payload: '해산물' },
      { label: '💸 비싼 곳', payload: '비싼 곳' },
      { label: '👥 사람 많은 곳', payload: '사람 많은 곳' },
      { label: '✅ 없음 / 다 좋아', payload: '' }
    ]
  },
  en: {
    title: 'Duribeon',
    tagline: 'Spontaneous quests, only here, only now',
    language: 'Language',

    resetBtn: 'Start over',
    journalBtn: 'Journal',

    composerPlaceholder: 'Tap a button or type freely...',
    send: 'Send',

    estimated: 'ETA',
    minutes: 'min',
    proof: 'Proof',
    route: 'Route',
    pick: 'Take this',
    swap: 'Swap',

    uploadLabel: 'Arrived? Drop a photo',
    uploadHint: 'JPG / PNG · tap to pick',
    uploadOrDrop: 'Click or drag a photo here',
    dropHere: '⬇ Drop here ⬇',
    selectPhoto: '📷 Pick photo',
    changePhoto: 'Change',
    submitPhoto: 'Submit',

    pass: 'Passed!',
    fail: 'Hmm, try again?',

    greet:
      "Hey! I'm Duribeon. Just a few quick questions and I'll cook up five back-alley quests.",
    askArea: 'Which neighborhood are you in? 👀',
    ackArea: (a) => `${a}, good pick.`,
    askGroup: "Who's with you?",
    ackGroup: 'Got it, noted.',
    askTime: "How much time do you have? I'll size the quests to fit.",
    ackTime: 'Time noted.',
    askMood: "What's the vibe today? Pick one.",
    ackMood: 'Locked in.',
    askAvoid: 'Last one — anything to avoid? (Type multiples freely)',
    ackAvoid: "Got it. Let me wander the alleys for a sec.",
    generating: 'Hold on, peeking around the corners...',
    presentMissions: 'Here are five quests. Pick one that hits.',
    ackPick: (t) => `Oh, "${t}". Solid pick.`,
    promptPhoto: 'When you arrive and proof time, drop a photo here.',
    verifying: 'Inspecting your photo...',
    promptNext: 'Another quest?',

    fallbackUnknown:
      "Hmm, didn't catch that. Tap one of the buttons below 😅",
    fallbackPhotoNeeded: 'Proof needs a photo — drop one in.',
    fallbackBusy: 'Hold on, working on it...',
    fallbackNoMoreSwap:
      'No fresh quests left in this neighborhood — putting that one back.',

    errorPrefix: 'Error',

    qrSkip: 'Skip',
    qrAnyMood: '🎲 Surprise me',
    qrSubmit: 'Submit',
    qrRerollAll: '🔄 Reroll all',
    qrAnotherMission: '✨ Another quest',
    qrStartOver: '🏠 Start over',
    qrRetry: '🔄 Retry',
    ackRetry: (t) => `Oh, retrying "${t}". Let's go again.`,

    journalTitle: 'Travel journal',
    journalEmpty: 'No missions logged yet. Go try one!',
    journalCount: (n) => `${n} mission${n === 1 ? '' : 's'} logged`,
    clearJournal: 'Clear all',
    clearConfirm: 'Wipe everything? Cannot be undone.',
    closeJournal: 'Close',
    resetConfirm:
      'Start the chat over? Anything in progress will be lost.',

    panelTitle: 'Quest pool',
    panelEmpty:
      "Your quests will stack up here.\nAnswer the bot and I'll cook five up.",
    panelCount: (n) => `${n}`,
    panelOpenMobile: 'Open quest pool',
    panelCloseMobile: 'Close',
    panelMissionsReady: 'Five quests ready.',
    panelLookRight: 'Pick one from the panel on the right →',
    panelStateActive: 'Active',
    panelStatePassed: 'Passed',
    panelStateFailed: 'Failed',
    panelStateRejected: 'Rejected',
    panelStatePool: 'Available',
    panelGenerateMore: '✨ Brew five more',
    panelTakeFromPool: 'Take',
    panelChangeFromPool: 'Reroll',
    panelRejectFromPool: 'Reject',
    ackChange: (title) => `OK, rerolling "${title}" — same place, different angle.`,
    ackChangeDone: (title) => `Here you go: "${title}". How about this one?`,
    ackReject: (title) => `OK, dropping "${title}".`,

    areasUnavailable: "Couldn't fetch areas. Make sure the backend is running.",

    groupOptions: [
      { label: '🧍 Solo', payload: 'solo' },
      { label: '💕 Couple', payload: 'couple' },
      { label: '🤝 Two of us', payload: '2 friends' },
      { label: '🍻 Three of us', payload: '3 friends' },
      { label: '🎉 Four+ of us', payload: '4+ friends' }
    ],
    timeOptions: [
      { label: '⚡ Just 30 min', payload: '~30 min' },
      { label: '🍵 1–2 hours', payload: '1-2 hours' },
      { label: '🌳 Half a day', payload: 'half day' },
      { label: '🌙 Until evening', payload: 'all day' }
    ],
    moodOptions: [
      { label: '💭 Moody / wistful', payload: 'wistful, atmospheric' },
      { label: '🔥 Push my limits', payload: 'challenging' },
      { label: '🌿 Quiet & chill', payload: 'quiet healing' },
      { label: '🤣 Make me laugh', payload: 'fun and silly' },
      { label: '🤝 Deep local', payload: 'deep local experience' },
      { label: '📷 Photogenic', payload: 'photogenic' }
    ],
    avoidOptions: [
      { label: '🌶 Spicy', payload: 'spicy food' },
      { label: '🍷 Alcohol', payload: 'alcohol' },
      { label: '🐟 Seafood', payload: 'seafood' },
      { label: '💸 Pricey spots', payload: 'expensive places' },
      { label: '👥 Crowded places', payload: 'crowded places' },
      { label: '✅ Nothing to avoid', payload: '' }
    ]
  }
};
