<script lang="ts">
  import type { Language, PanelMission, PanelMissionState } from './types';
  import { I18N } from './i18n';

  export let language: Language;
  export let panel: PanelMission[];
  export let busy = false;
  export let drawerOpen = false;
  export let changingId: string | null = null;
  export let onTake: (pm: PanelMission) => void = () => {};
  export let onChange: (pm: PanelMission) => void = () => {};
  export let onReject: (pm: PanelMission) => void = () => {};
  export let onRetry: (pm: PanelMission) => void = () => {};
  export let onClose: () => void = () => {};
  export let onGenerateMore: () => void = () => {};
  export let canGenerateMore = false;

  $: t = I18N[language];

  /* show newest first; sort by ts within group */
  $: ordered = [...panel].sort((a, b) => {
    const stateRank: Record<PanelMissionState, number> = {
      active: 0,
      pool: 1,
      passed: 2,
      failed: 3,
      rejected: 4
    };
    const ra = stateRank[a.state];
    const rb = stateRank[b.state];
    if (ra !== rb) return ra - rb;
    const ta = a.completedAt ?? a.pickedAt ?? a.generatedAt;
    const tb = b.completedAt ?? b.pickedAt ?? b.generatedAt;
    return tb - ta;
  });

  function stateLabel(s: PanelMissionState): string {
    switch (s) {
      case 'active': return t.panelStateActive;
      case 'pool': return t.panelStatePool;
      case 'passed': return t.panelStatePassed;
      case 'failed': return t.panelStateFailed;
      case 'rejected': return t.panelStateRejected;
    }
  }
</script>

<aside class="mission-panel" class:open={drawerOpen} aria-label={t.panelTitle}>
  <header class="panel-head">
    <div>
      <h2>📂 {t.panelTitle}</h2>
      <span class="count">{t.panelCount(panel.length)}</span>
    </div>
    <div class="panel-head-actions">
      {#if canGenerateMore}
        <button class="more" disabled={busy} on:click={onGenerateMore}>
          {t.panelGenerateMore}
        </button>
      {/if}
      <button
        class="close"
        on:click={onClose}
        aria-label={t.panelCloseMobile}
      >
        ✕
      </button>
    </div>
  </header>

  <div class="panel-body">
    {#if ordered.length === 0}
      <div class="panel-empty">{t.panelEmpty}</div>
    {:else}
      {#each ordered as pm (pm.mission.id)}
        <article class="pcard pcard-{pm.state}">
          <header class="pcard-head">
            <span class="state-badge state-{pm.state}">{stateLabel(pm.state)}</span>
            <span class="cat-badge">{pm.mission.category}</span>
            <span class="eta">⏱ {pm.mission.estimated_minutes}{t.minutes}</span>
          </header>
          <h3>{pm.mission.title}</h3>
          <p class="hook">{pm.mission.hook}</p>
          <p class="place">📍 {pm.mission.place_name}</p>

          {#if pm.state === 'pool'}
            <div class="meta">
              <p class="row"><b>{t.route}</b>{pm.mission.route_hint}</p>
              <p class="row"><b>{t.proof}</b>{pm.mission.proof_method}</p>
            </div>
            <div class="actions">
              <button class="primary" disabled={busy} on:click={() => onTake(pm)}>
                {t.panelTakeFromPool}
              </button>
              <button class="ghost" disabled={busy} on:click={() => onChange(pm)}>
                {#if changingId === pm.mission.id}<span class="spinner" />{/if}
                {t.panelChangeFromPool}
              </button>
              <button class="ghost" disabled={busy} on:click={() => onReject(pm)}>
                {t.panelRejectFromPool}
              </button>
            </div>
          {:else if pm.state === 'active'}
            <div class="meta">
              <p class="row"><b>{t.route}</b>{pm.mission.route_hint}</p>
              <p class="row"><b>{t.proof}</b>{pm.mission.proof_method}</p>
            </div>
            <div class="active-note">📷 …</div>
          {:else if pm.state === 'passed' || pm.state === 'failed'}
            {#if pm.thumbnail}
              <div class="thumb"><img src={pm.thumbnail} alt="proof" /></div>
            {/if}
            {#if pm.verdict}
              <p class="verdict-line">💬 {pm.verdict.comment}</p>
            {/if}
            {#if pm.state === 'failed'}
              <div class="actions">
                <button class="primary" disabled={busy} on:click={() => onRetry(pm)}>
                  {t.qrRetry}
                </button>
              </div>
            {/if}
          {/if}
        </article>
      {/each}
    {/if}
  </div>
</aside>

<style>
  .mission-panel {
    background: var(--bg);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    width: 360px;
    flex-shrink: 0;
    height: 100dvh;
    overflow: hidden;
  }

  .panel-head {
    padding: 0.85rem 1rem;
    background: linear-gradient(135deg, var(--accent-soft), #fff7eb);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }
  .panel-head h2 {
    margin: 0;
    font-family: var(--serif);
    font-weight: 900;
    font-size: 1.15rem;
    color: var(--accent-deep);
    display: inline;
  }
  .panel-head .count {
    color: var(--text-dim);
    font-size: 0.78rem;
    margin-left: 0.4rem;
  }

  .panel-head-actions {
    display: flex;
    gap: 0.4rem;
    align-items: center;
  }
  .panel-head-actions .more {
    background: linear-gradient(135deg, var(--accent), var(--accent-deep));
    color: #fff;
    border: 1px solid var(--accent-deep);
    border-radius: 999px;
    padding: 0.4rem 0.8rem;
    font-weight: 700;
    font-size: 0.78rem;
    cursor: pointer;
    box-shadow: 0 3px 10px rgba(255, 122, 61, 0.25);
  }
  .panel-head-actions .more:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }
  .panel-head-actions .close {
    background: rgba(255,255,255,0.7);
    border: 1px solid var(--border-strong);
    width: 32px; height: 32px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 0.95rem;
    display: none;
    align-items: center;
    justify-content: center;
  }

  .panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 0.9rem;
  }
  .panel-empty {
    color: var(--text-dim);
    font-style: italic;
    text-align: center;
    padding: 2rem 1rem;
    white-space: pre-line;
    line-height: 1.6;
  }

  .pcard {
    background: #fff;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.85rem;
    margin-bottom: 0.7rem;
    box-shadow: var(--shadow-sm);
    transition: opacity 0.2s ease, transform 0.15s ease;
    animation: pop 0.18s ease-out;
  }
  .pcard-rejected {
    opacity: 0.55;
    background: var(--bg-soft);
  }
  .pcard-active {
    border-color: var(--accent);
    box-shadow: 0 4px 16px rgba(255, 122, 61, 0.25);
    background: linear-gradient(180deg, #fff, #fff8ef);
  }
  .pcard-passed {
    border-color: var(--pass);
    background: linear-gradient(180deg, #fff, var(--pass-soft));
  }
  .pcard-failed {
    border-color: var(--fail);
    background: linear-gradient(180deg, #fff, var(--fail-soft));
  }

  .pcard-head {
    display: flex;
    gap: 0.35rem;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
    align-items: center;
  }
  .state-badge {
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    padding: 0.18rem 0.5rem;
    border-radius: 6px;
    text-transform: uppercase;
    font-family: var(--mono);
  }
  .state-pool { color: var(--accent-deep); background: var(--accent-soft); }
  .state-active { color: #fff; background: var(--accent); }
  .state-passed { color: var(--pass); background: var(--pass-soft); }
  .state-failed { color: var(--fail); background: var(--fail-soft); }
  .state-rejected { color: var(--text-dim); background: var(--bg-soft); }

  .cat-badge {
    font-size: 0.7rem;
    color: var(--secondary);
    background: var(--secondary-soft);
    border: 1px solid var(--secondary);
    border-radius: 999px;
    padding: 0.1rem 0.5rem;
    font-weight: 600;
  }
  .eta {
    margin-left: auto;
    font-size: 0.72rem;
    color: var(--text-dim);
    font-family: var(--mono);
  }

  .pcard h3 {
    margin: 0 0 0.3rem;
    font-family: var(--serif);
    font-weight: 800;
    font-size: 1.02rem;
    color: var(--text);
    letter-spacing: -0.01em;
  }
  .pcard .hook {
    margin: 0 0 0.5rem;
    color: var(--text-dim);
    font-style: italic;
    font-size: 0.85rem;
    line-height: 1.4;
  }
  .pcard .place {
    margin: 0 0 0.55rem;
    color: var(--accent-deep);
    font-size: 0.82rem;
    font-weight: 600;
  }

  .meta { margin-bottom: 0.6rem; }
  .row {
    margin: 0 0 0.3rem;
    font-size: 0.83rem;
    line-height: 1.4;
  }
  .row b {
    color: var(--accent-deep);
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-right: 0.35rem;
    font-weight: 700;
  }

  .actions {
    display: flex;
    gap: 0.4rem;
  }
  .actions button {
    flex: 1;
    border-radius: 10px;
    padding: 0.5rem 0.7rem;
    font-weight: 700;
    font-size: 0.82rem;
    cursor: pointer;
    border: 1px solid var(--border-strong);
  }
  .actions button.primary {
    background: linear-gradient(135deg, var(--accent), var(--accent-deep));
    color: #fff;
    border-color: var(--accent-deep);
    box-shadow: 0 2px 8px rgba(255, 122, 61, 0.22);
  }
  .actions button.primary:disabled {
    opacity: 0.5; cursor: not-allowed; box-shadow: none;
  }
  .actions button.ghost {
    background: transparent;
    color: var(--text);
  }
  .actions button.ghost:hover { background: var(--bg-soft); }
  .actions button.ghost:disabled { opacity: 0.5; cursor: not-allowed; }

  .active-note {
    text-align: center;
    color: var(--accent-deep);
    font-weight: 700;
    font-size: 0.85rem;
    padding: 0.4rem;
    background: var(--accent-soft);
    border-radius: 8px;
  }

  .thumb {
    margin: 0.4rem 0;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid var(--border);
  }
  .thumb img {
    display: block;
    width: 100%;
    height: 140px;
    object-fit: cover;
  }
  .verdict-line {
    margin: 0.4rem 0 0;
    font-size: 0.85rem;
    line-height: 1.4;
    font-weight: 600;
  }

  .spinner {
    display: inline-block;
    width: 11px; height: 11px;
    border: 2px solid var(--border-strong);
    border-top-color: var(--accent-deep);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    vertical-align: -1px;
    margin-right: 0.35rem;
  }

  @keyframes pop {
    from { transform: translateY(6px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* mobile: drawer */
  @media (max-width: 900px) {
    .mission-panel {
      position: fixed;
      top: 0; right: 0;
      height: 100dvh;
      width: 88%;
      max-width: 380px;
      transform: translateX(100%);
      transition: transform 0.25s ease-out;
      box-shadow: -10px 0 30px rgba(0, 0, 0, 0.18);
      z-index: 25;
      border-left: 1px solid var(--border-strong);
    }
    .mission-panel.open { transform: translateX(0); }
    .panel-head-actions .close { display: inline-flex; }
  }
</style>
