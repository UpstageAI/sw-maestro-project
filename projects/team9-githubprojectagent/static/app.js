"use strict";

const sid = new URLSearchParams(location.search).get("sid");
if (!sid) location.href = "/";

const $ = (id) => document.getElementById(id);
const thread = $("thread");

const STATE_LABELS = {
  INIT: "초기화",
  FETCHING: "GitHub 레포 가져오는 중",
  COMPRESSING: "커밋·README 압축 요약",
  INTERVIEWING: "추가 정보 분석 중",
  GENERATING: "4섹션 병렬 생성",
  VALIDATING: "채점",
  REFINING: "약한 섹션 재생성",
  DIAGRAMMING: "다이어그램 생성",
  MERGING: "최종 머지",
  READY_FOR_TEMPLATE: "템플릿 선택 단계",
  PUBLISHING: "Notion 발행",
  DONE: "완료",
  ERROR: "오류",
  ABORTED: "중단됨",
};
const TERMINAL_STATES = new Set(["DONE", "ERROR", "ABORTED", "READY_FOR_TEMPLATE"]);
const RUNNING = new Set([
  "INIT","FETCHING","COMPRESSING","INTERVIEWING","GENERATING",
  "VALIDATING","REFINING","DIAGRAMMING","MERGING","PUBLISHING",
]);

// 진행 단계 순서 — step-bar에서 done/active 표시용
const STEP_ORDER = [
  "FETCHING","COMPRESSING","INTERVIEWING","GENERATING",
  "VALIDATING","DIAGRAMMING","MERGING","READY_FOR_TEMPLATE",
];
function stepIndex(state) {
  // VALIDATING과 REFINING은 같은 단계로 묶음
  if (state === "REFINING") return STEP_ORDER.indexOf("VALIDATING");
  if (state === "PUBLISHING" || state === "DONE") return STEP_ORDER.length;
  return STEP_ORDER.indexOf(state);
}

// ---- 마크다운 → HTML (가벼운 라인 기반) ----
function escHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function inlineMd(s) {
  return escHtml(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
}
function renderMd(md) {
  if (!md) return "";
  const lines = md.split("\n");
  const out = [];
  let inCode = false;
  let codeLang = "";
  let codeBuf = [];
  let inList = false;
  let codeIdx = 0;
  const closeList = () => { if (inList) { out.push("</ul>"); inList = false; } };

  for (const line of lines) {
    if (line.startsWith("```")) {
      if (inCode) {
        const body = codeBuf.join("\n");
        if (codeLang === "mermaid") {
          const id = `mmd-${Date.now()}-${codeIdx++}`;
          out.push(`<div class="mermaid-host"><pre class="mermaid" id="${id}">${escHtml(body)}</pre></div>`);
        } else {
          out.push("<pre><code>" + escHtml(body) + "</code></pre>");
        }
        codeBuf = []; inCode = false; codeLang = "";
      } else {
        closeList();
        codeLang = line.slice(3).trim();
        inCode = true;
      }
      continue;
    }
    if (inCode) { codeBuf.push(line); continue; }
    if (/^---+\s*$/.test(line)) { closeList(); out.push("<hr>"); continue; }
    let m = line.match(/^(#{1,3})\s+(.*)/);
    if (m) {
      closeList();
      out.push(`<h${m[1].length}>${inlineMd(m[2])}</h${m[1].length}>`);
      continue;
    }
    m = line.match(/^\s*[-*]\s+(.*)/);
    if (m) {
      if (!inList) { out.push("<ul>"); inList = true; }
      out.push(`<li>${inlineMd(m[1])}</li>`);
      continue;
    }
    m = line.match(/^>\s+(.*)/);
    if (m) {
      closeList();
      out.push(`<blockquote>${inlineMd(m[1])}</blockquote>`);
      continue;
    }
    if (line.trim() === "") { closeList(); continue; }
    closeList();
    out.push(`<p>${inlineMd(line)}</p>`);
  }
  closeList();
  if (inCode) out.push("<pre><code>" + escHtml(codeBuf.join("\n")) + "</code></pre>");
  return out.join("\n");
}

async function renderMermaidIn(rootEl) {
  const nodes = rootEl.querySelectorAll("pre.mermaid");
  if (!nodes.length) return;
  // 노드별로 try — 일부 실패해도 다른 건 렌더
  for (const node of nodes) {
    try {
      await mermaid.run({ nodes: [node] });
    } catch (e) {
      console.warn("mermaid render fail:", e);
      // 폴백: 원본 mermaid 코드 + 에러 메시지를 코드블록으로 표시
      const original = node.textContent;
      const errMsg = (e && e.message) ? e.message : String(e);
      const wrapper = document.createElement("div");
      wrapper.className = "mermaid-fallback";
      wrapper.innerHTML = `
        <div class="mermaid-error">⚠ 다이어그램 렌더 실패 (Mermaid syntax error). 원본 코드:</div>
        <pre><code>${escHtml(original)}</code></pre>
        <details><summary>에러 상세</summary><pre>${escHtml(errMsg)}</pre></details>
      `;
      node.replaceWith(wrapper);
    }
  }
}

// ---- 메시지 누적 ----
const messageIds = new Set();

function addMsg(role, html, msgId = null) {
  if (msgId && messageIds.has(msgId)) return null;
  if (msgId) messageIds.add(msgId);
  const m = document.createElement("div");
  m.className = `msg ${role}`;
  if (msgId) m.dataset.msgid = msgId;
  const avatarHtml =
    role === "user" ? '<div class="avatar user">U</div>'
    : role === "system" ? '<div class="avatar sys">·</div>'
    : '<div class="avatar ai">★</div>';
  m.innerHTML = `${avatarHtml}<div class="body"><div class="bubble"></div></div>`;
  m.querySelector(".bubble").innerHTML = html;
  thread.appendChild(m);
  thread.scrollTop = thread.scrollHeight;
  return m;
}

function setStatePill(state, ageSec) {
  const pill = $("state-pill");
  pill.classList.remove("running","done","error");
  if (state === "DONE") pill.classList.add("done");
  else if (state === "ERROR" || state === "ABORTED") pill.classList.add("error");
  else pill.classList.add("running");
  $("state-label").textContent = state;
}

function updateStepBar(state) {
  const idx = stepIndex(state);
  const steps = document.querySelectorAll(".step-bar .step");
  steps.forEach((el, i) => {
    el.classList.remove("done", "active");
    const stepName = el.dataset.step;
    const stepIdx = STEP_ORDER.indexOf(stepName);
    if (stepIdx < idx) el.classList.add("done");
    else if (stepIdx === idx) el.classList.add("active");
  });
}

function updateActivityStrip(state, log, ageSec) {
  const strip = $("activity-strip");
  const text = $("activity-text");
  strip.classList.remove("idle", "stuck", "error");

  if (state === "DONE") { strip.classList.add("idle"); text.textContent = "완료"; return; }
  if (state === "ERROR" || state === "ABORTED") {
    strip.classList.add("error");
    text.textContent = state === "ABORTED" ? "사용자가 중단함" : "오류 발생";
    return;
  }
  if (state === "READY_FOR_TEMPLATE") {
    strip.classList.add("idle");
    text.textContent = "템플릿 선택 대기 중";
    return;
  }

  // 가장 최근 로그 라인 추출 (set_state 또는 progress 콜백)
  const last = (log && log.length) ? log[log.length - 1] : "";
  // [HH:MM:SS] STATE — msg → "msg" 또는 "  → msg" 부분만
  let pretty = last
    .replace(/^\[[^\]]+\]\s*/, "")    // 시각 제거
    .replace(/^[A-Z_]+\s*—\s*/, "")    // 상태명 제거
    .replace(/^\s*→\s*/, "");          // 화살표 제거
  if (!pretty) pretty = STATE_LABELS[state] || state;

  text.textContent = pretty;

  // 60초 이상 같은 상태면 stuck 경고
  if (ageSec > 60) strip.classList.add("stuck");
}

function fmtDuration(sec) {
  if (sec < 60) return `${sec.toFixed(0)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}m ${s}s`;
}

// ---- Composer ----
function showComposer({ contentHtml, hint, onSubmit, submitLabel = "제출" }) {
  $("composer-content").innerHTML = contentHtml;
  $("composer-hint").textContent = hint || "";
  $("composer-submit").textContent = submitLabel;
  $("composer-err").textContent = "";
  $("composer-submit").disabled = false;
  $("composer").classList.remove("hidden");
  $("composer-submit").onclick = async () => {
    $("composer-submit").disabled = true;
    try {
      await onSubmit();
    } catch (e) {
      $("composer-err").textContent = "에러: " + e.message;
      $("composer-submit").disabled = false;
    }
  };
}
function hideComposer() {
  $("composer").classList.add("hidden");
  $("composer-content").innerHTML = "";
}

// ---- 섹션 렌더 ----
function upsertSection(name, title, content) {
  const id = `sec-${name}`;
  let msg = thread.querySelector(`[data-msgid="${id}"]`);
  const html = `
    <div class="role">AI · 섹션</div>
    <div class="section-card">
      <h3>${title}</h3>
      <div class="markdown">${renderMd(content)}</div>
    </div>
  `;
  if (msg) {
    msg.querySelector(".bubble").innerHTML = html;
  } else {
    msg = addMsg("assistant", html, id);
  }
  return msg;
}

function upsertScores(verdict, history) {
  const id = "scores";
  if (!verdict) return;
  let msg = thread.querySelector(`[data-msgid="${id}"]`);
  const passOverall = verdict.overall_pass;
  const html = `
    <div class="role">AI · 채점</div>
    <div class="score-panel">
      <div class="score-summary">
        ${passOverall ? "✓ 통과" : "⚠ 약한 섹션 — " + verdict.weakest}
      </div>
      ${verdict.scores.map(s => `
        <div class="score-row">
          <span class="name">${s.name}</span>
          <span class="${s.score >= 90 ? 'pass' : 'fail'}">${s.score}</span>
        </div>
        <div class="rationale">${s.rationale}</div>
      `).join("")}
      <div class="round-info">리파인 라운드: ${history.length}</div>
    </div>
  `;
  if (msg) msg.querySelector(".bubble").innerHTML = html;
  else addMsg("assistant", html, id);
}

function upsertDiagram(name, title, mermaidText) {
  const id = `diag-${name}`;
  if (!mermaidText) return;
  let msg = thread.querySelector(`[data-msgid="${id}"]`);
  const html = `
    <div class="role">AI · 다이어그램</div>
    <div class="section-card">
      <h3>${title}</h3>
      <div class="mermaid-host"><pre class="mermaid">${escHtml(mermaidText)}</pre></div>
    </div>
  `;
  if (msg) msg.querySelector(".bubble").innerHTML = html;
  else msg = addMsg("assistant", html, id);
  renderMermaidIn(msg);
}

let templatesLoaded = false;
let selectedTemplateId = null;

async function showTemplates() {
  if (templatesLoaded) return;
  templatesLoaded = true;
  const r = await fetch(`/api/session/${sid}/templates`);
  if (!r.ok) return;
  const { templates } = await r.json();

  const cardsHtml = templates.map(t => `
    <div class="template-card" data-id="${t.id}">
      <h4>${t.name}</h4>
      <p>${t.description}</p>
      <button type="button" class="preview-btn" data-toggle="${t.id}">미리보기 펼치기 ▾</button>
      <div class="template-preview hidden" data-pv="${t.id}"></div>
    </div>
  `).join("");

  const tplPreviews = Object.fromEntries(templates.map(t => [t.id, t.preview_md]));

  const html = `
    <div class="role">AI · 템플릿 후보</div>
    <div class="section-card">
      <h3>템플릿 선택</h3>
      <p class="muted-sm">하나 골라서 Notion 또는 PDF로 출력. 카드 클릭으로 선택, '미리보기'로 본문 확인.</p>
      <div class="template-grid">${cardsHtml}</div>
    </div>
  `;
  const msg = addMsg("assistant", html, "templates");

  msg.querySelectorAll(".template-card").forEach(card => {
    card.addEventListener("click", (e) => {
      if (e.target.classList.contains("preview-btn")) return;
      msg.querySelectorAll(".template-card").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      selectedTemplateId = card.dataset.id;
      showPublishComposer(templates);
    });
  });
  msg.querySelectorAll(".preview-btn").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const tid = btn.dataset.toggle;
      const pv = msg.querySelector(`[data-pv="${tid}"]`);
      if (pv.classList.contains("hidden")) {
        pv.innerHTML = `<div class="markdown">${renderMd(tplPreviews[tid])}</div>`;
        pv.classList.remove("hidden");
        btn.textContent = "미리보기 접기 ▴";
        renderMermaidIn(pv);
      } else {
        pv.classList.add("hidden");
        btn.textContent = "미리보기 펼치기 ▾";
      }
    });
  });
}

function showPublishComposer(templates) {
  const tplName = templates.find(t => t.id === selectedTemplateId)?.name || selectedTemplateId;
  $("composer-content").innerHTML = `
    <div class="composer-title">선택: <strong>${tplName}</strong></div>
    <div class="field"><input id="cp-token" type="password" placeholder="Notion Token (Notion 발행 시)"></div>
    <div class="field"><input id="cp-parent" type="text" placeholder="Notion Parent Page ID (Notion 발행 시)"></div>
  `;
  $("composer-hint").textContent = "PDF는 즉시 다운로드 / Notion은 토큰 필요";
  $("composer-err").textContent = "";

  const actions = $("composer").querySelector(".composer-actions");
  const old = actions.querySelector("#composer-pdf");
  if (old) old.remove();

  const pdfBtn = document.createElement("button");
  pdfBtn.id = "composer-pdf";
  pdfBtn.className = "ghost";
  pdfBtn.textContent = "📄 PDF로 저장";
  actions.insertBefore(pdfBtn, $("composer-submit"));

  const submitBtn = $("composer-submit");
  submitBtn.textContent = "📝 Notion으로 발행";
  submitBtn.disabled = false;
  submitBtn.className = "primary";

  $("composer").classList.remove("hidden");

  pdfBtn.onclick = async () => {
    pdfBtn.disabled = true; submitBtn.disabled = true;
    $("composer-err").textContent = "";
    try {
      const r = await fetch(`/api/session/${sid}/export-pdf`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template_id: selectedTemplateId }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || `HTTP ${r.status}`);
      }
      const j = await r.json();
      if (!j.success) throw new Error(j.error || "PDF 생성 실패");
      hideComposer();
      addMsg("user", `PDF로 저장: ${tplName}`);
      addMsg("assistant", `
        <div class="role">AI · PDF 생성 완료</div>
        <div class="done-banner">
          <h3>📄 PDF 저장 완료</h3>
          <p><a href="${j.download_url}" download="${j.filename}">${j.filename} — 다운로드</a></p>
          <p class="meta">로컬 경로: <code>${j.absolute_path}</code></p>
        </div>
      `);
      const a = document.createElement("a");
      a.href = j.download_url; a.download = j.filename;
      document.body.appendChild(a); a.click(); a.remove();
    } catch (e) {
      $("composer-err").textContent = "PDF 에러: " + e.message;
      pdfBtn.disabled = false; submitBtn.disabled = false;
    }
  };

  submitBtn.onclick = async () => {
    pdfBtn.disabled = true; submitBtn.disabled = true;
    $("composer-err").textContent = "";
    try {
      const r = await fetch(`/api/session/${sid}/publish`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_id: selectedTemplateId,
          notion_token: $("cp-token").value || null,
          notion_parent_page_id: $("cp-parent").value || null,
        }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || `HTTP ${r.status}`);
      }
      hideComposer();
      addMsg("user", `Notion 발행: ${tplName}`);
    } catch (e) {
      $("composer-err").textContent = "Notion 에러: " + e.message;
      pdfBtn.disabled = false; submitBtn.disabled = false;
    }
  };
}

// ---- 인터뷰 ----
let interviewShown = false;
function showInterview(questions) {
  if (interviewShown) return;
  interviewShown = true;
  const qsHtml = questions.map((q, i) =>
    `<p><strong>Q${i+1}.</strong> ${escHtml(q)}</p>`
  ).join("");
  addMsg("assistant", `
    <div class="role">AI · 추가 정보 요청</div>
    <div class="section-card">
      <h3>몇 가지 질문이 있습니다</h3>
      <p class="muted-sm">4섹션을 더 정확하게 작성하기 위해 답해주세요. 모르면 비워둬도 OK.</p>
      ${qsHtml}
    </div>
  `, "interview-q");

  const composerInputs = questions.map((q, i) =>
    `<textarea id="ans-${i}" rows="2" placeholder="Q${i+1} 답변 (생략 가능)"></textarea>`
  ).join("");

  showComposer({
    contentHtml: composerInputs,
    hint: `${questions.length}개 질문 — 답변 후 4섹션 생성 시작`,
    submitLabel: "답변 제출",
    onSubmit: async () => {
      const answers = questions.map((_, i) => $(`ans-${i}`).value);
      const r = await fetch(`/api/session/${sid}/answers`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || `HTTP ${r.status}`);
      }
      const userText = questions.map((q, i) => {
        const a = answers[i].trim();
        return a ? `Q${i+1}: ${a}` : null;
      }).filter(Boolean).join("\n") || "(모두 비움)";
      addMsg("user", escHtml(userText).replace(/\n/g, "<br>"));
      hideComposer();
    },
  });
}

function showDone(publishResult) {
  if (!publishResult) return;
  const cls = publishResult.success ? "" : "warn";
  const icon = publishResult.success ? "✓" : "⚠";
  const title = publishResult.success ? "Notion 발행 성공" : "Notion 발행 실패 — 로컬 백업만 생성됨";
  const link = publishResult.page_url
    ? `<a class="url" href="${publishResult.page_url}" target="_blank">${publishResult.page_url}</a>`
    : "";
  addMsg("assistant", `
    <div class="role">AI · 완료</div>
    <div class="done-banner ${cls}">
      <h3>${icon} ${title}</h3>
      ${link}
      ${publishResult.error ? `<p class="meta">${escHtml(publishResult.error)}</p>` : ""}
      <p class="meta">백업: <code>${publishResult.backup_path}</code></p>
    </div>
  `, "done");
}

// ---- abort ----
$("abort-btn").addEventListener("click", async () => {
  if (!confirm("현재 분석을 중단하시겠습니까? 이미 시작된 LLM 호출은 끝까지 실행될 수 있습니다.")) return;
  $("abort-btn").disabled = true;
  try {
    await fetch(`/api/session/${sid}/abort`, { method: "POST" });
  } catch (e) {
    console.warn("abort fail", e);
  }
});

// ---- 로그 ----
let lastLogIdx = 0;
function appendLogs(logs) {
  for (let i = lastLogIdx; i < logs.length; i++) {
    addMsg("system", `<span>${escHtml(logs[i])}</span>`, `log-${i}`);
  }
  lastLogIdx = logs.length;
}

// ---- 폴링 (backoff) ----
let pollDelay = 1500;
let lastObservedState = null;

async function poll() {
  try {
    const r = await fetch(`/api/session/${sid}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const s = await r.json();

    setStatePill(s.state, s.state_age_sec);
    updateStepBar(s.state);
    updateActivityStrip(s.state, s.log, s.state_age_sec || 0);
    if (typeof s.elapsed_sec === "number") {
      $("elapsed").textContent = fmtDuration(s.elapsed_sec);
    }
    // 60초 이상 정체 시 사용자 안내 (한 번만)
    if ((s.state_age_sec || 0) > 60 && !window._stuckTipShown) {
      window._stuckTipShown = true;
      addMsg("system", `
        <strong>💡 진행이 60초 이상 멈춰있습니다.</strong><br>
        ${s.state === "FETCHING"
          ? "GitHub rate limit 가능성 — PAT 없이 1시간에 60콜만 허용됩니다. 새로고침 후 PAT를 입력해 재시도하거나, 1시간 뒤 다시 시도하세요."
          : "LLM 응답이 느리거나 막혔을 수 있습니다. 우상단 '중단' 버튼으로 끊고 다시 시도하세요."}
      `, "stuck-tip");
    }

    if (s.repo_full_name) {
      $("title").textContent = s.repo_full_name;
      $("repo-name").textContent = s.repo_url || "";
    }

    appendLogs(s.log || []);

    // 인터뷰
    if (s.state === "INTERVIEWING" && s.questions.length > 0 && s.answers.length === 0) {
      showInterview(s.questions);
    }

    const titles = {
      problem: "문제 인식",
      status: "현황 파악",
      cause: "원인 분석 및 해결책",
      result: "결과 정리 및 성능 향상",
    };
    for (const k of ["problem","status","cause","result"]) {
      if (s.draft[k]) upsertSection(k, titles[k], s.draft[k].content);
    }

    if (s.verdict) upsertScores(s.verdict, s.history);
    if (s.draft.architecture) upsertDiagram("architecture", "시스템 아키텍처", s.draft.architecture);
    if (s.draft.dataflow) upsertDiagram("dataflow", "데이터 플로우", s.draft.dataflow);

    // READY_FOR_TEMPLATE 진입은 한 번만 처리 — 이후 폴링이 hideComposer/showTemplates를 다시
    // 호출하면, 사용자가 템플릿 카드 클릭해서 띄운 발행 composer가 사라지는 버그 발생.
    if (s.state === "READY_FOR_TEMPLATE" && !templatesLoaded) {
      hideComposer();
      await showTemplates();
    }

    // abort 버튼: 진행 중일 때만 노출
    const inProgress = !TERMINAL_STATES.has(s.state) && s.state !== "DONE";
    $("abort-btn").classList.toggle("hidden", !inProgress);

    if (s.state === "DONE") {
      hideComposer();
      $("abort-btn").classList.add("hidden");
      showDone(s.publish_result);
      return;
    }

    if (s.state === "ERROR" || s.state === "ABORTED") {
      hideComposer();
      $("abort-btn").classList.add("hidden");
      addMsg("assistant", `
        <div class="role">AI · ${s.state === "ABORTED" ? "중단됨" : "오류"}</div>
        <div class="done-banner err">
          <h3>${s.state === "ABORTED" ? "⏹ 중단됨" : "❌ 오류"}</h3>
          <p>${escHtml(s.error || "(unknown)")}</p>
        </div>
      `, "err");
      return;
    }

    // backoff: 같은 상태 30초 이상이면 5초로
    if (s.state === lastObservedState && s.state_age_sec > 30) {
      pollDelay = 5000;
    } else {
      pollDelay = 1500;
    }
    lastObservedState = s.state;
  } catch (e) {
    console.warn("poll error", e);
  }
  setTimeout(poll, pollDelay);
}

poll();
