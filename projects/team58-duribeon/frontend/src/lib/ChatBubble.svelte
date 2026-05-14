<script lang="ts">
  import type { ChatMessage, Language, Mission } from './types';
  import { I18N } from './i18n';
  import { shortTime } from './storage';

  export let message: ChatMessage;
  export let language: Language;
  export let busy = false;
  export let onSelectPhoto: (file: File, mission: Mission) => void = () => {};
  export let onSubmitPhoto: (mission: Mission) => void = () => {};
  export let pendingPhotoPreview = '';
  export let pendingPhotoMissionId: string | null = null;

  $: t = I18N[language];

  // Drag-and-drop state for the photo_upload card.
  let dragging = false;
  let dragDepth = 0;

  function handlePhotoChange(e: Event, mission: Mission) {
    const input = e.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (file) onSelectPhoto(file, mission);
  }

  function handleDragEnter(e: DragEvent) {
    if (message.consumed) return;
    if (!e.dataTransfer || !Array.from(e.dataTransfer.types).includes('Files')) return;
    e.preventDefault();
    dragDepth += 1;
    dragging = true;
  }

  function handleDragOver(e: DragEvent) {
    // preventDefault is what enables `drop` on this element
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
  }

  function handleDragLeave() {
    dragDepth -= 1;
    if (dragDepth <= 0) {
      dragDepth = 0;
      dragging = false;
    }
  }

  function handleDrop(e: DragEvent, mission: Mission) {
    // Without preventDefault the browser's default action runs *after* our
    // handler — which is "navigate to the dropped file" (i.e. open the image
    // in a new tab). Block it.
    e.preventDefault();
    dragDepth = 0;
    dragging = false;
    if (message.consumed) return;
    const file = e.dataTransfer?.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) return;
    onSelectPhoto(file, mission);
  }
</script>

<div class="msg msg-{message.role}">
  {#if message.role === 'bot'}
    <div class="avatar" aria-hidden="true">두</div>
  {/if}

  <div class="bubble-col">
    <div class="bubble">
      {#if message.content.kind === 'text'}
        <p class="text">{message.content.text}</p>
      {:else if message.content.kind === 'photo_upload'}
        {@const mission = message.content.mission}
        {@const isPending = pendingPhotoMissionId === mission.id}
        <div
          class="upload-card"
          class:dragging
          role="region"
          aria-label={t.uploadOrDrop}
          on:dragenter={handleDragEnter}
          on:dragover={handleDragOver}
          on:dragleave={handleDragLeave}
          on:drop={(e) => handleDrop(e, mission)}
        >
          <div class="upload-title">📷 {t.uploadLabel}</div>
          <div class="upload-mission">"{mission.title}"</div>
          {#if !message.consumed && !pendingPhotoPreview && !message.content.thumbnail}
            <div class="upload-or-drop-hint">{t.uploadOrDrop}</div>
          {/if}
          {#if dragging && !message.consumed}
            <div class="drop-hint">{t.dropHere}</div>
          {/if}
          {#if message.content.thumbnail || (isPending && pendingPhotoPreview)}
            <div class="preview">
              <img
                src={message.content.thumbnail ?? pendingPhotoPreview}
                alt="proof preview"
              />
            </div>
          {/if}
          {#if !message.consumed}
            <div class="upload-actions">
              <label class="file-btn">
                <input
                  type="file"
                  accept="image/jpeg,image/png"
                  on:change={(e) => handlePhotoChange(e, mission)}
                />
                {isPending ? t.changePhoto : t.selectPhoto}
              </label>
              <button
                class="primary"
                disabled={!isPending || busy}
                on:click={() => onSubmitPhoto(mission)}
              >
                {#if busy && isPending}<span class="spinner" />{/if}{t.submitPhoto}
              </button>
            </div>
          {/if}
        </div>
      {:else if message.content.kind === 'verdict'}
        {@const v = message.content.verdict}
        <div class="verdict-card">
          <div class="verdict-head">
            <span class="stamp {v.ok ? 'pass' : 'fail'}">
              {v.ok ? t.pass : t.fail}
            </span>
            <strong>{message.content.mission.title}</strong>
          </div>
          {#if message.content.thumbnail}
            <div class="preview"><img src={message.content.thumbnail} alt="proof" /></div>
          {/if}
          <p class="verdict-comment">💬 {v.comment}</p>
          <p class="verdict-reason">{v.reason}</p>
        </div>
      {/if}
    </div>

    <span class="ts">{shortTime(message.ts, language)}</span>
  </div>
</div>

<style>
  .msg {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.85rem;
    animation: pop 0.18s ease-out;
  }
  .msg-user { flex-direction: row-reverse; }
  .msg-user .bubble-col { align-items: flex-end; }
  .msg-bot .bubble-col { align-items: flex-start; }

  .avatar {
    flex-shrink: 0;
    width: 32px; height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--accent), var(--accent-deep));
    color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-weight: 900;
    font-size: 0.95rem;
    box-shadow: var(--shadow-sm);
    margin-top: 2px;
  }

  .bubble-col {
    display: flex;
    flex-direction: column;
    max-width: calc(100% - 44px);
    min-width: 0;
  }

  .bubble {
    padding: 0.7rem 0.95rem;
    border-radius: 18px;
    font-size: 0.95rem;
    line-height: 1.45;
    word-break: break-word;
  }
  .msg-bot .bubble {
    background: #f5f0e8;
    border: 1px solid var(--border);
    color: var(--text);
    border-top-left-radius: 4px;
  }
  .msg-user .bubble {
    background: linear-gradient(135deg, var(--accent), var(--accent-deep));
    color: #fff;
    border-top-right-radius: 4px;
    box-shadow: 0 2px 8px rgba(255, 122, 61, 0.18);
  }
  .bubble .text { margin: 0; white-space: pre-wrap; }

  .ts {
    font-size: 0.7rem;
    color: var(--text-dim);
    margin-top: 0.3rem;
    padding: 0 0.4rem;
  }

  /* photo upload card (rendered inside bot bubble) */
  .upload-card {
    background: #fff;
    border: 2px dashed var(--border-strong);
    border-radius: 14px;
    padding: 0.95rem;
    margin: -0.2rem -0.2rem;
    transition: border-color 0.15s ease, background 0.15s ease,
                box-shadow 0.15s ease, transform 0.1s ease;
  }
  .upload-card.dragging {
    border-color: var(--accent);
    border-style: solid;
    background: var(--accent-soft);
    box-shadow: 0 0 0 4px rgba(255, 122, 61, 0.18);
    transform: scale(1.01);
  }
  .upload-title { font-weight: 700; margin-bottom: 0.2rem; font-size: 0.95rem; }
  .upload-mission {
    color: var(--text-dim);
    font-size: 0.85rem;
    margin-bottom: 0.6rem;
    font-style: italic;
  }
  .drop-hint {
    text-align: center;
    color: var(--accent-deep);
    font-weight: 700;
    font-size: 0.9rem;
    padding: 0.6rem;
    margin-bottom: 0.6rem;
    background: rgba(255, 255, 255, 0.7);
    border-radius: 10px;
    pointer-events: none;
  }
  .upload-or-drop-hint {
    color: var(--text-dim);
    font-size: 0.78rem;
    text-align: center;
    margin-bottom: 0.5rem;
  }
  .upload-actions {
    display: flex;
    gap: 0.45rem;
    margin-top: 0.6rem;
  }
  .upload-actions .file-btn {
    flex: 1;
    text-align: center;
    background: var(--bg-elev);
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    padding: 0.55rem 0.85rem;
    font-weight: 600;
    font-size: 0.85rem;
    cursor: pointer;
  }
  .upload-actions .file-btn:hover { background: var(--accent-soft); border-color: var(--accent); }
  .upload-actions .file-btn input { display: none; }
  .upload-actions button.primary {
    flex: 1;
    background: linear-gradient(135deg, var(--accent), var(--accent-deep));
    color: #fff;
    border: 1px solid var(--accent-deep);
    border-radius: 10px;
    padding: 0.55rem 0.85rem;
    font-weight: 700;
    font-size: 0.85rem;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(255, 122, 61, 0.22);
  }
  .upload-actions button.primary:disabled {
    opacity: 0.5; cursor: not-allowed; box-shadow: none;
  }

  .preview {
    margin: 0.6rem 0 0;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--border);
  }
  .preview img {
    display: block;
    width: 100%;
    max-height: 320px;
    object-fit: cover;
  }

  .verdict-card { padding: 0; }
  .verdict-head {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin-bottom: 0.6rem;
    flex-wrap: wrap;
  }
  .verdict-head strong { font-family: var(--serif); font-weight: 800; }
  .stamp {
    display: inline-block;
    font-weight: 800;
    font-size: 1.1rem;
    padding: 0.3rem 0.8rem;
    border: 3px solid currentColor;
    border-radius: 8px;
    transform: rotate(-6deg);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-family: var(--mono);
  }
  .stamp.pass { color: var(--pass); background: var(--pass-soft); }
  .stamp.fail { color: var(--fail); background: var(--fail-soft); }
  .verdict-comment { margin: 0.5rem 0 0.3rem; font-weight: 600; }
  .verdict-reason { margin: 0; color: var(--text-dim); font-size: 0.85rem; }

  .spinner {
    display: inline-block;
    width: 12px; height: 12px;
    border: 2px solid rgba(255, 255, 255, 0.4);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    vertical-align: -2px;
    margin-right: 0.4rem;
  }

  @keyframes pop {
    from { transform: translateY(8px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
