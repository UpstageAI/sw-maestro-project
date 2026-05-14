<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';
  import { fetchAreas, generateMissions, regenerateMission, verifyPhoto } from '$lib/api';
  import { I18N } from '$lib/i18n';
  import ChatBubble from '$lib/ChatBubble.svelte';
  import MissionPanel from '$lib/MissionPanel.svelte';
  import {
    appendJournal,
    clearChat,
    clearJournal,
    fileToThumbnail,
    formatTimestamp,
    loadChat,
    loadJournal,
    loadLanguage,
    saveChat,
    saveLanguage,
    type JournalEntry
  } from '$lib/storage';
  import {
    CHAT_STATE_VERSION,
    type Area,
    type AreaInfo,
    type ChatMessage,
    type ChatState,
    type ContextInput,
    type Language,
    type Mission,
    type PanelMission,
    type PanelMissionState,
    type QuickReply,
    type Step
  } from '$lib/types';

  /* ========================  state  ======================== */
  let language: Language = 'ko';
  $: t = I18N[language];

  let messages: ChatMessage[] = [];
  let step: Step = 'greet';
  let context: Partial<ContextInput> = {};
  let selectedMissionId: string | null = null;
  let rejectedPlaceIds: string[] = [];
  let panel: PanelMission[] = [];
  let busy = false;
  let isBotTyping = false;
  let changingId: string | null = null;

  let composerText = '';
  let composerEl: HTMLInputElement | null = null;

  let pendingPhotoFile: File | null = null;
  let pendingPhotoPreview = '';
  let pendingPhotoMissionId: string | null = null;

  let journal: JournalEntry[] = [];
  let journalOpen = false;

  let drawerOpen = false;

  // Areas fetched from /api/areas (data-driven from seed JSON).
  let areas: AreaInfo[] = [];
  let areasError = '';

  let mounted = false;
  let scrollEnd: HTMLDivElement | null = null;

  $: dockedQuickReplies = (() => {
    if (busy) return null;
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === 'bot' && m.quickReplies?.length && !m.consumed) {
        return m.quickReplies;
      }
    }
    return null;
  })();

  $: poolCount = panel.filter((p) => p.state === 'pool').length;

  /* ========================  ids  ======================== */
  function uid() {
    return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
  }

  /* ========================  persistence  ======================== */
  $: if (mounted) saveLanguage(language);

  $: if (mounted) {
    const snapshot: ChatState = {
      version: CHAT_STATE_VERSION,
      messages,
      step,
      context,
      selectedMissionId,
      rejectedPlaceIds,
      panel
    };
    saveChat(snapshot);
  }

  /* ========================  utilities  ======================== */
  async function scrollToBottom(smooth = true) {
    await tick();
    scrollEnd?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'end' });
  }

  function pushBot(content: ChatMessage['content'], quickReplies?: QuickReply[]): ChatMessage {
    const m: ChatMessage = {
      id: uid(),
      role: 'bot',
      ts: Date.now(),
      content,
      quickReplies
    };
    messages = [...messages, m];
    return m;
  }

  function pushUser(text: string): ChatMessage {
    const m: ChatMessage = {
      id: uid(),
      role: 'user',
      ts: Date.now(),
      content: { kind: 'text', text }
    };
    messages = [...messages, m];
    return m;
  }

  function consumeLastQuickReplies() {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === 'bot' && m.quickReplies?.length && !m.consumed) {
        messages[i] = { ...m, consumed: true };
        messages = [...messages];
        return;
      }
    }
  }

  function delay(ms: number) {
    return new Promise<void>((r) => setTimeout(r, ms));
  }

  async function botTypeBriefly(ms = 450) {
    isBotTyping = true;
    await scrollToBottom();
    await delay(ms);
    isBotTyping = false;
  }

  /* ========================  panel ops  ======================== */
  function addPanelMissions(missions: Mission[]) {
    const now = Date.now();
    // Override the LLM-supplied `id` (which is non-unique across calls — Solar
    // tends to reuse "m1"…"m5" every response) with a frontend-generated uid.
    // Without this, Svelte's keyed each block (`{#each ordered as pm
    // (pm.mission.id)}`) sees duplicate keys and silently drops the new card.
    const additions: PanelMission[] = missions.map((m) => ({
      mission: { ...m, id: uid() },
      state: 'pool' as PanelMissionState,
      generatedAt: now
    }));
    panel = [...panel, ...additions];
  }

  function setPanelState(missionId: string, next: PanelMissionState) {
    panel = panel.map((p) =>
      p.mission.id === missionId
        ? {
            ...p,
            state: next,
            pickedAt: next === 'active' ? Date.now() : p.pickedAt,
            completedAt:
              next === 'passed' || next === 'failed' ? Date.now() : p.completedAt
          }
        : p
    );
  }

  function rejectAllPool() {
    panel = panel.map((p) => (p.state === 'pool' ? { ...p, state: 'rejected' } : p));
  }

  /* ========================  conversation  ======================== */
  function areaLabel(id: string | undefined): string {
    if (!id) return '';
    const a = areas.find((x) => x.id === id);
    if (!a) return id;
    return language === 'ko' ? a.name_ko : a.name_en;
  }

  function quickRepliesForArea(): QuickReply[] {
    return areas.map((a) => ({
      label: `📍 ${language === 'ko' ? a.name_ko : a.name_en}`,
      intent: 'set_area',
      payload: a.id
    }));
  }
  function quickRepliesForGroup(): QuickReply[] {
    return t.groupOptions.map((opt) => ({
      label: opt.label,
      intent: 'set_group',
      payload: opt.payload
    }));
  }
  function quickRepliesForTime(): QuickReply[] {
    return t.timeOptions.map((opt) => ({
      label: opt.label,
      intent: 'set_time',
      payload: opt.payload
    }));
  }
  function quickRepliesForMood(): QuickReply[] {
    return [
      ...t.moodOptions.map((opt) => ({
        label: opt.label,
        intent: 'set_mood' as const,
        payload: opt.payload
      })),
      { label: t.qrAnyMood, intent: 'set_mood', payload: 'balanced' }
    ];
  }
  function quickRepliesForAvoid(): QuickReply[] {
    return t.avoidOptions.map((opt) => ({
      label: opt.label,
      intent: 'set_avoid',
      payload: opt.payload
    }));
  }
  function quickRepliesAfterCards(): QuickReply[] {
    return [
      { label: t.qrRerollAll, intent: 'reroll_all' },
      { label: t.qrStartOver, intent: 'reset' }
    ];
  }
  function quickRepliesAfterVerdict(): QuickReply[] {
    return [
      { label: t.qrAnotherMission, intent: 'restart_after_verdict' },
      { label: t.qrStartOver, intent: 'reset' }
    ];
  }

  async function startGreeting() {
    isBotTyping = true;
    await scrollToBottom(false);
    await delay(350);
    pushBot({ kind: 'text', text: t.greet });
    await delay(220);
    pushBot({ kind: 'text', text: t.askArea }, quickRepliesForArea());
    isBotTyping = false;
    step = 'ask_area';
    await scrollToBottom();
  }

  async function botAskTime() {
    pushBot({ kind: 'text', text: t.ackGroup });
    await delay(180);
    pushBot({ kind: 'text', text: t.askTime }, quickRepliesForTime());
    step = 'ask_time';
    await scrollToBottom();
  }

  async function botAskMood() {
    pushBot({ kind: 'text', text: t.ackTime });
    await delay(180);
    pushBot({ kind: 'text', text: t.askMood }, quickRepliesForMood());
    step = 'ask_mood';
    await scrollToBottom();
  }

  async function botAskAvoid() {
    pushBot({ kind: 'text', text: t.ackMood });
    await delay(180);
    pushBot({ kind: 'text', text: t.askAvoid }, quickRepliesForAvoid());
    step = 'ask_avoid';
    await scrollToBottom();
  }

  async function botGenerate() {
    pushBot({ kind: 'text', text: t.ackAvoid });
    await scrollToBottom();
    step = 'generating';
    busy = true;
    isBotTyping = true;
    await scrollToBottom();
    try {
      const ctx: ContextInput = {
        area: (context.area ?? areas[0]?.id ?? 'ikseon') as Area,
        group: context.group ?? t.groupOptions[1].payload,
        timeBudget: context.timeBudget ?? '1~2시간',
        mood: context.mood && context.mood.length > 0 ? context.mood : 'balanced',
        avoid: context.avoid ?? '',
        language
      };
      context = ctx;
      const fresh = await generateMissions(ctx, rejectedPlaceIds);
      addPanelMissions(fresh);
      isBotTyping = false;
      pushBot(
        { kind: 'text', text: `${t.panelMissionsReady} ${t.panelLookRight}` },
        quickRepliesAfterCards()
      );
      step = 'show_missions';
      // Open drawer on mobile so users see the panel.
      drawerOpen = true;
    } catch (e) {
      isBotTyping = false;
      pushBot({ kind: 'text', text: `${t.errorPrefix}: ${(e as Error).message}` });
    } finally {
      busy = false;
      await scrollToBottom();
    }
  }

  async function rerollAll() {
    if (!context.area) return;
    consumeLastQuickReplies();
    pushUser(t.qrRerollAll);
    busy = true;
    isBotTyping = true;
    await scrollToBottom();
    try {
      const currentPool = panel.filter((p) => p.state === 'pool');
      rejectedPlaceIds = [
        ...rejectedPlaceIds,
        ...currentPool.map((p) => p.mission.place_id)
      ];
      rejectAllPool();
      const ctx = {
        area: context.area as Area,
        group: context.group ?? t.groupOptions[1].payload,
        timeBudget: context.timeBudget ?? '1~2시간',
        mood: context.mood ?? 'balanced',
        avoid: context.avoid ?? '',
        language
      };
      const fresh = await generateMissions(ctx, rejectedPlaceIds);
      addPanelMissions(fresh);
      isBotTyping = false;
      pushBot(
        { kind: 'text', text: `${t.panelMissionsReady} ${t.panelLookRight}` },
        quickRepliesAfterCards()
      );
      step = 'show_missions';
      drawerOpen = true;
    } catch (e) {
      isBotTyping = false;
      pushBot({ kind: 'text', text: `${t.errorPrefix}: ${(e as Error).message}` });
    } finally {
      busy = false;
      await scrollToBottom();
    }
  }

  /**
   * 바꿔: keep the same place, regenerate mission text only. Calls the
   * dedicated /api/missions/regenerate endpoint and replaces the mission
   * fields (title, hook, route_hint, proof_method, ETA, category) in place.
   * The frontend-assigned panel uid is preserved so Svelte's keyed each
   * doesn't unmount/remount the card.
   */
  async function changeMissionAtSamePlace(pm: PanelMission) {
    if (!context.area || pm.state !== 'pool' || busy) return;
    changingId = pm.mission.id;
    busy = true;
    pushUser(`${t.panelChangeFromPool}: ${pm.mission.title}`);
    await botTypeBriefly(280);
    pushBot({ kind: 'text', text: t.ackChange(pm.mission.title) });
    isBotTyping = true;
    await scrollToBottom();
    try {
      const ctx: ContextInput = {
        area: context.area as Area,
        group: context.group ?? t.groupOptions[1].payload,
        timeBudget: context.timeBudget ?? '1~2시간',
        mood: context.mood ?? 'balanced',
        avoid: context.avoid ?? '',
        language
      };
      const fresh = await regenerateMission(ctx, pm.mission.place_id, pm.mission.title);
      // Replace mission contents in place, preserving the panel uid.
      panel = panel.map((p) =>
        p.mission.id === pm.mission.id
          ? {
              ...p,
              mission: {
                ...fresh,
                id: pm.mission.id,
                place_id: pm.mission.place_id,
                place_name: pm.mission.place_name
              }
            }
          : p
      );
      isBotTyping = false;
      pushBot({ kind: 'text', text: t.ackChangeDone(fresh.title) });
      await scrollToBottom();
    } catch (e) {
      isBotTyping = false;
      pushBot({ kind: 'text', text: `${t.errorPrefix}: ${(e as Error).message}` });
      await scrollToBottom();
    } finally {
      changingId = null;
      busy = false;
    }
  }

  /**
   * 거절: simply mark the mission as rejected. No replacement, no LLM call.
   * The user can still pull more via "✨ 새로 5개" if they exhaust their pool.
   */
  function rejectFromPanel(pm: PanelMission) {
    if (pm.state !== 'pool' || busy) return;
    pushUser(`${t.panelRejectFromPool}: ${pm.mission.title}`);
    rejectedPlaceIds = [...rejectedPlaceIds, pm.mission.place_id];
    setPanelState(pm.mission.id, 'rejected');
    pushBot({ kind: 'text', text: t.ackReject(pm.mission.title) });
  }

  /**
   * Returns any currently-active mission to `pool` and consumes its in-chat
   * photo upload bubble. Also clears any selected-but-unsubmitted photo.
   * Called before activating a new mission so only one is active at a time.
   */
  function deactivatePreviousActive() {
    if (!selectedMissionId) return;
    const prevId = selectedMissionId;
    panel = panel.map((p) =>
      p.mission.id === prevId && p.state === 'active'
        ? { ...p, state: 'pool', pickedAt: undefined }
        : p
    );
    messages = messages.map((m) =>
      m.role === 'bot' &&
      m.content.kind === 'photo_upload' &&
      m.content.mission.id === prevId
        ? { ...m, consumed: true }
        : m
    );
    if (pendingPhotoMissionId === prevId) {
      if (pendingPhotoPreview) URL.revokeObjectURL(pendingPhotoPreview);
      pendingPhotoFile = null;
      pendingPhotoPreview = '';
      pendingPhotoMissionId = null;
    }
    selectedMissionId = null;
  }

  async function pickFromPanel(pm: PanelMission) {
    if (pm.state !== 'pool' || busy) return;
    consumeLastQuickReplies();
    deactivatePreviousActive();
    setPanelState(pm.mission.id, 'active');
    selectedMissionId = pm.mission.id;
    pushUser(`${t.pick}: ${pm.mission.title}`);
    drawerOpen = false;
    await botTypeBriefly(400);
    pushBot({ kind: 'text', text: t.ackPick(pm.mission.title) });
    await delay(180);
    pushBot({ kind: 'text', text: t.promptPhoto });
    pushBot({ kind: 'photo_upload', mission: pm.mission });
    step = 'await_photo';
    await scrollToBottom();
  }

  async function retryFailed(pm: PanelMission) {
    if (pm.state !== 'failed' || busy) return;
    consumeLastQuickReplies();
    deactivatePreviousActive();
    // Move the failed card back to active and clear last attempt's verdict /
    // thumbnail (journal still keeps the failure permanently).
    panel = panel.map((p) =>
      p.mission.id === pm.mission.id
        ? {
            ...p,
            state: 'active',
            verdict: undefined,
            thumbnail: undefined,
            completedAt: undefined,
            pickedAt: Date.now()
          }
        : p
    );
    selectedMissionId = pm.mission.id;
    pushUser(`${t.qrRetry}: ${pm.mission.title}`);
    drawerOpen = false;
    await botTypeBriefly(400);
    pushBot({ kind: 'text', text: t.ackRetry(pm.mission.title) });
    await delay(180);
    pushBot({ kind: 'text', text: t.promptPhoto });
    pushBot({ kind: 'photo_upload', mission: pm.mission });
    step = 'await_photo';
    await scrollToBottom();
  }

  async function selectPhoto(file: File, mission: Mission) {
    pendingPhotoFile = file;
    pendingPhotoMissionId = mission.id;
    if (pendingPhotoPreview) URL.revokeObjectURL(pendingPhotoPreview);
    pendingPhotoPreview = URL.createObjectURL(file);
  }

  async function submitPhoto(mission: Mission) {
    if (!pendingPhotoFile || pendingPhotoMissionId !== mission.id) return;
    busy = true;
    step = 'verifying';

    let thumbnail: string | undefined;
    try {
      thumbnail = await fileToThumbnail(pendingPhotoFile, 320);
    } catch (_) {
      thumbnail = undefined;
    }

    const photoFile = pendingPhotoFile;
    const photoMissionId = pendingPhotoMissionId;
    if (pendingPhotoPreview) URL.revokeObjectURL(pendingPhotoPreview);
    pendingPhotoPreview = '';
    pendingPhotoFile = null;
    pendingPhotoMissionId = null;

    messages = messages.map((m) =>
      m.role === 'bot' &&
      m.content.kind === 'photo_upload' &&
      m.content.mission.id === photoMissionId
        ? { ...m, consumed: true, content: { ...m.content, thumbnail } }
        : m
    );

    pushUser(t.qrSubmit);
    isBotTyping = true;
    await scrollToBottom();

    try {
      const verdict = await verifyPhoto(photoFile, mission, language);
      isBotTyping = false;
      pushBot({ kind: 'verdict', mission, verdict, thumbnail });
      panel = panel.map((p) =>
        p.mission.id === mission.id
          ? {
              ...p,
              state: verdict.ok ? 'passed' : 'failed',
              verdict,
              thumbnail,
              completedAt: Date.now()
            }
          : p
      );
      try {
        const journalEntry: JournalEntry = {
          ts: Date.now(),
          language,
          mission,
          verdict,
          thumbnail
        };
        appendJournal(journalEntry);
        journal = loadJournal();
      } catch (_) {}
      await delay(280);
      pushBot({ kind: 'text', text: t.promptNext }, quickRepliesAfterVerdict());
      step = 'show_verdict';
      selectedMissionId = null;
    } catch (e) {
      isBotTyping = false;
      pushBot({ kind: 'text', text: `${t.errorPrefix}: ${(e as Error).message}` });
    } finally {
      busy = false;
      await scrollToBottom();
    }
  }

  async function generateMore() {
    if (!context.area || busy) return;
    consumeLastQuickReplies();
    pushUser(t.qrAnotherMission);
    busy = true;
    isBotTyping = true;
    await scrollToBottom();
    try {
      const ctx = {
        area: context.area as Area,
        group: context.group ?? t.groupOptions[1].payload,
        timeBudget: context.timeBudget ?? '1~2시간',
        mood: context.mood ?? 'balanced',
        avoid: context.avoid ?? '',
        language
      };
      const fresh = await generateMissions(ctx, rejectedPlaceIds);
      addPanelMissions(fresh);
      isBotTyping = false;
      pushBot(
        { kind: 'text', text: `${t.panelMissionsReady} ${t.panelLookRight}` },
        quickRepliesAfterCards()
      );
      step = 'show_missions';
      drawerOpen = true;
    } catch (e) {
      isBotTyping = false;
      pushBot({ kind: 'text', text: `${t.errorPrefix}: ${(e as Error).message}` });
    } finally {
      busy = false;
      await scrollToBottom();
    }
  }

  /* ========================  intent dispatch  ======================== */
  async function handleQuickReply(qr: QuickReply) {
    if (busy) return;
    consumeLastQuickReplies();

    switch (qr.intent) {
      case 'set_area': {
        const area = qr.payload as Area;
        context = { ...context, area };
        pushUser(qr.label);
        await botTypeBriefly(320);
        // Use the clean area name (without 📍 emoji) in the ack.
        pushBot({ kind: 'text', text: t.ackArea(areaLabel(area)) });
        await delay(180);
        pushBot({ kind: 'text', text: t.askGroup }, quickRepliesForGroup());
        step = 'ask_group';
        await scrollToBottom();
        break;
      }
      case 'set_group': {
        context = { ...context, group: qr.payload as string };
        pushUser(qr.label);
        await botTypeBriefly(320);
        await botAskTime();
        break;
      }
      case 'set_time': {
        context = { ...context, timeBudget: qr.payload as string };
        pushUser(qr.label);
        await botTypeBriefly(320);
        await botAskMood();
        break;
      }
      case 'set_mood': {
        context = { ...context, mood: qr.payload as string };
        pushUser(qr.label);
        await botTypeBriefly(320);
        await botAskAvoid();
        break;
      }
      case 'set_avoid': {
        context = { ...context, avoid: (qr.payload as string) ?? '' };
        pushUser(qr.label);
        await botTypeBriefly(320);
        await botGenerate();
        break;
      }
      case 'reroll_all':
        await rerollAll();
        break;
      case 'reset':
        await resetChat();
        break;
      case 'restart_after_verdict':
        await generateMore();
        break;
    }
  }

  /* ========================  free-text routing  ======================== */
  async function handleSend() {
    const text = composerText.trim();
    if (!text || busy) return;
    composerText = '';

    const lower = text.toLowerCase();

    if (
      /^(처음|리셋|새로|다시\s*시작)/.test(text) ||
      /^(reset|start over|restart)\b/.test(lower)
    ) {
      pushUser(text);
      await resetChat();
      return;
    }

    if (step === 'ask_area') {
      const matched = matchArea(text);
      if (matched) {
        await handleQuickReply({
          label: areaLabel(matched),
          intent: 'set_area',
          payload: matched
        });
        return;
      }
    }
    if (step === 'ask_group') {
      pushUser(text);
      context = { ...context, group: text };
      await botTypeBriefly(280);
      await botAskTime();
      return;
    }
    if (step === 'ask_time') {
      pushUser(text);
      context = { ...context, timeBudget: text };
      await botTypeBriefly(280);
      await botAskMood();
      return;
    }
    if (step === 'ask_mood') {
      pushUser(text);
      context = { ...context, mood: text };
      await botTypeBriefly(280);
      await botAskAvoid();
      return;
    }
    if (step === 'ask_avoid') {
      pushUser(text);
      context = { ...context, avoid: text };
      await botTypeBriefly(280);
      await botGenerate();
      return;
    }

    if (step === 'show_missions' || step === 'show_verdict') {
      if (
        /^(다른|다 별로|reroll|all again|nah)/.test(lower) ||
        text.includes('다시')
      ) {
        pushUser(text);
        if (step === 'show_missions') await rerollAll();
        else await generateMore();
        return;
      }
      const idx = parsePickIndex(text);
      if (idx != null) {
        const pool = panel.filter((p) => p.state === 'pool');
        const target = pool[idx];
        if (target) {
          await pickFromPanel(target);
          return;
        }
      }
    }

    if (step === 'await_photo') {
      pushUser(text);
      await botTypeBriefly(220);
      pushBot({ kind: 'text', text: t.fallbackPhotoNeeded });
      await scrollToBottom();
      return;
    }

    if (step === 'verifying' || step === 'generating') {
      pushUser(text);
      await botTypeBriefly(220);
      pushBot({ kind: 'text', text: t.fallbackBusy });
      await scrollToBottom();
      return;
    }

    pushUser(text);
    await botTypeBriefly(260);
    pushBot({ kind: 'text', text: t.fallbackUnknown });
    await scrollToBottom();
  }

  function parsePickIndex(text: string): number | null {
    const m = text.match(/(\d+)/);
    if (m) {
      const n = parseInt(m[1], 10);
      if (n >= 1 && n <= 5) return n - 1;
    }
    const koMap: Record<string, number> = {
      첫: 0, 첫번째: 0, 두: 1, 두번째: 1, 세: 2, 세번째: 2,
      네: 3, 네번째: 3, 다섯: 4, 다섯번째: 4
    };
    for (const [k, v] of Object.entries(koMap)) {
      if (text.includes(k)) return v;
    }
    const enMap: Record<string, number> = {
      first: 0, second: 1, third: 2, fourth: 3, fifth: 4
    };
    for (const [k, v] of Object.entries(enMap)) {
      if (text.toLowerCase().includes(k)) return v;
    }
    return null;
  }

  function matchArea(text: string): Area | null {
    const lower = text.toLowerCase();
    for (const a of areas) {
      for (const kw of a.match_ko) {
        if (kw && text.includes(kw)) return a.id;
      }
      for (const kw of a.match_en) {
        if (kw && lower.includes(kw.toLowerCase())) return a.id;
      }
    }
    return null;
  }

  /* ========================  reset / journal  ======================== */
  async function resetChat() {
    if (typeof window !== 'undefined' && messages.length > 1) {
      if (!window.confirm(t.resetConfirm)) return;
    }
    messages = [];
    step = 'greet';
    context = {};
    selectedMissionId = null;
    rejectedPlaceIds = [];
    panel = [];
    drawerOpen = false;
    if (pendingPhotoPreview) URL.revokeObjectURL(pendingPhotoPreview);
    pendingPhotoFile = null;
    pendingPhotoPreview = '';
    pendingPhotoMissionId = null;
    busy = false;
    isBotTyping = false;
    clearChat();
    await startGreeting();
  }

  function openJournal() {
    journal = loadJournal();
    journalOpen = true;
  }

  function closeJournal() {
    journalOpen = false;
  }

  function handleClearJournal() {
    if (typeof window !== 'undefined' && !window.confirm(t.clearConfirm)) return;
    clearJournal();
    journal = [];
  }

  function setLanguage(next: Language) {
    language = next;
  }

  /* ========================  init  ======================== */
  // Block the browser from navigating to a dropped file when the user misses
  // the upload card. The card's own drop handler still receives the file
  // first (events bubble child→parent); this just kills the default action
  // for everything that would otherwise leak to the document.
  const blockFileDrop = (e: DragEvent) => {
    if (e.dataTransfer && Array.from(e.dataTransfer.types).includes('Files')) {
      e.preventDefault();
    }
  };

  onMount(async () => {
    language = loadLanguage();
    journal = loadJournal();

    window.addEventListener('dragover', blockFileDrop);
    window.addEventListener('drop', blockFileDrop);

    // Fetch curated areas from /api/areas — drives quick replies and matchers.
    try {
      areas = await fetchAreas();
      areasError = '';
    } catch (e) {
      areasError = (e as Error).message || t.areasUnavailable;
      areas = [];
    }

    const saved = loadChat();
    if (saved && saved.messages.length > 0) {
      messages = saved.messages;
      step = saved.step;
      context = saved.context;
      selectedMissionId = saved.selectedMissionId;
      rejectedPlaceIds = saved.rejectedPlaceIds ?? [];
      panel = saved.panel ?? [];
      mounted = true;
      tick().then(() => scrollToBottom(false));
    } else {
      mounted = true;
      startGreeting();
    }
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('dragover', blockFileDrop);
      window.removeEventListener('drop', blockFileDrop);
    }
  });

  $: if (mounted && (messages.length || isBotTyping)) {
    tick().then(() => scrollEnd?.scrollIntoView({ behavior: 'smooth', block: 'end' }));
  }
</script>

<div class="app-shell">
  <div class="chat-app">
    <header class="topbar">
      <div class="lang-toggle" role="group" aria-label={t.language}>
        <button class:on={language === 'ko'} on:click={() => setLanguage('ko')}>한국어</button>
        <button class:on={language === 'en'} on:click={() => setLanguage('en')}>English</button>
      </div>
      <div class="topbar-right">
        <button class="icon-btn" on:click={resetChat} aria-label={t.resetBtn}>
          🏠 <span class="hide-sm">{t.resetBtn}</span>
        </button>
        <button class="icon-btn" on:click={openJournal} aria-label={t.journalBtn}>
          📓 <span class="hide-sm">{t.journalBtn}</span>
          {#if journal.length > 0}<span class="badge">{journal.length}</span>{/if}
        </button>
        <button
          class="icon-btn drawer-btn"
          on:click={() => (drawerOpen = !drawerOpen)}
          aria-label={t.panelOpenMobile}
        >
          📂 <span class="hide-sm">{t.panelTitle}</span>
          {#if poolCount > 0}<span class="badge accent">{poolCount}</span>{/if}
        </button>
      </div>
    </header>

    <main class="messages">
      <div class="brand-header">
        <h1>{t.title} <span class="plane">✈︎</span></h1>
        <p class="tag">{t.tagline}</p>
      </div>

      {#if areasError}
        <div class="boot-error">⚠️ {areasError}</div>
      {/if}

      {#each messages as m (m.id)}
        <ChatBubble
          message={m}
          {language}
          {busy}
          {pendingPhotoPreview}
          {pendingPhotoMissionId}
          onSelectPhoto={selectPhoto}
          onSubmitPhoto={submitPhoto}
        />
      {/each}

      {#if isBotTyping}
        <div class="typing-row">
          <div class="avatar">두</div>
          <div class="bubble typing">
            <span class="dot" /><span class="dot" /><span class="dot" />
          </div>
        </div>
      {/if}

      <div bind:this={scrollEnd} class="scroll-end" />
    </main>

    {#if dockedQuickReplies}
      <div class="docked-qr" aria-label="quick replies">
        {#each dockedQuickReplies as qr}
          <button
            class="qr-chip"
            disabled={busy}
            on:click={() => handleQuickReply(qr)}
          >
            {qr.label}
          </button>
        {/each}
      </div>
    {/if}

    <footer class="composer">
      <input
        bind:this={composerEl}
        type="text"
        bind:value={composerText}
        placeholder={t.composerPlaceholder}
        on:keydown={(e) => {
          if (e.key === 'Enter' && !e.isComposing) handleSend();
        }}
      />
      <button class="send" disabled={!composerText.trim() || busy} on:click={handleSend}>
        {t.send}
      </button>
    </footer>
  </div>

  {#if drawerOpen}
    <button
      class="panel-backdrop"
      on:click={() => (drawerOpen = false)}
      aria-label={t.panelCloseMobile}
    />
  {/if}

  <MissionPanel
    {language}
    {panel}
    {busy}
    {drawerOpen}
    {changingId}
    canGenerateMore={Boolean(context.area)}
    onTake={pickFromPanel}
    onChange={changeMissionAtSamePlace}
    onReject={rejectFromPanel}
    onRetry={retryFailed}
    onClose={() => (drawerOpen = false)}
    onGenerateMore={generateMore}
  />
</div>

{#if journalOpen}
  <div class="journal-backdrop">
    <div class="journal-sheet" role="dialog" aria-modal="true" aria-label={t.journalTitle}>
      <div class="journal-head">
        <div>
          <h2 style="display: inline;">📓 {t.journalTitle}</h2>
          <span class="count">{t.journalCount(journal.length)}</span>
        </div>
        <div style="display: flex; gap: 0.4rem;">
          {#if journal.length > 0}
            <button class="ghost" on:click={handleClearJournal}>{t.clearJournal}</button>
          {/if}
          <button on:click={closeJournal}>{t.closeJournal}</button>
        </div>
      </div>
      <div class="journal-body">
        {#if journal.length === 0}
          <div class="journal-empty">{t.journalEmpty}</div>
        {:else}
          {#each journal as e (e.ts + '-' + e.mission.id)}
            <div class="journal-entry">
              <div class="thumb">
                {#if e.thumbnail}
                  <img src={e.thumbnail} alt="proof" />
                {:else}
                  📷
                {/if}
              </div>
              <div style="flex: 1; min-width: 0;">
                <div class="meta-line">
                  <span class="verdict {e.verdict.ok ? 'pass' : 'fail'}">
                    {e.verdict.ok ? t.pass : t.fail}
                  </span>
                  <span class="ts">{formatTimestamp(e.ts, language)}</span>
                </div>
                <h4>{e.mission.title}</h4>
                <div class="place">📍 {e.mission.place_name}</div>
                <div class="comment">💬 {e.verdict.comment}</div>
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
{/if}
