const welcomeScreen = document.querySelector("#welcomeScreen");
const categoryScreen = document.querySelector("#categoryScreen");
const appScreen = document.querySelector("#appScreen");
const startButton = document.querySelector("#startButton");
const backButton = document.querySelector("#backButton");
const actionHelper = document.querySelector("#actionHelper");
const appActions = document.querySelector("#appActions");
const bottomNav = document.querySelector("#bottomNav");
const categoryCards = document.querySelectorAll(".category-card");
const appPages = document.querySelectorAll(".app-page");
const navItems = document.querySelectorAll(".nav-item");
const detailButtons = document.querySelectorAll("[data-detail-target]");
const detailBackButton = document.querySelector("#detailBackButton");
const openInlineQuizButton = document.querySelector("#openInlineQuizButton");
const inlineQuiz = document.querySelector("#inlineQuiz");
const quizStepDots = document.querySelectorAll("#quizStepDots span");
const quizQuestionLabel = document.querySelector("#quizQuestionLabel");
const quizQuestion = document.querySelector("#quizQuestion");
const quizFeedback = document.querySelector("#quizFeedback");
const quizFeedbackTitle = document.querySelector("#quizFeedbackTitle");
const quizFeedbackText = document.querySelector("#quizFeedbackText");
const quizNextButton = document.querySelector("#quizNextButton");
const oxButtons = document.querySelectorAll("[data-answer]");
const oxActions = document.querySelector(".ox-actions");
const quizResultSummary = document.querySelector("#quizResultSummary");

let currentStep = "welcome";
let homeLoadingTimer = null;
let currentQuizIndex = 0;
let quizScore = 0;
let quizSelections = [];

const detailQuizItems = [
  {
    question:
      "AI 검색 서비스는 검색 결과를 요약형 답변으로 보여주는 기능을 강화하고 있다.",
    answer: "O",
    explanation:
      "요약에서 검색 결과를 문장형 답변으로 제공하는 기능이 확대되고 있다고 설명했어요.",
  },
  {
    question:
      "사용자는 긴 기사 목록을 보기 전에 핵심 흐름과 배경을 먼저 확인할 수 있다.",
    answer: "O",
    explanation:
      "상세 요약은 사용자가 원문을 읽기 전에 맥락을 빠르게 잡도록 돕는 흐름이에요.",
  },
  {
    question: "이 기사에서 중요한 경쟁 포인트는 오프라인 배달 속도다.",
    answer: "X",
    explanation:
      "기사의 핵심은 출처 표시, 개인화 추천, 답변 품질 같은 AI 검색 경험에 있어요.",
  },
];

const resetInlineQuiz = () => {
  if (!inlineQuiz || !openInlineQuizButton) {
    return;
  }

  currentQuizIndex = 0;
  quizScore = 0;
  quizSelections = [];
  inlineQuiz.hidden = true;
  openInlineQuizButton.hidden = false;
  quizFeedback.hidden = true;
  quizNextButton.hidden = true;
  quizResultSummary.hidden = true;
  quizResultSummary.innerHTML = "";
  oxActions.hidden = false;

  oxButtons.forEach((button) => {
    button.classList.remove("is-selected");
    button.disabled = false;
  });
};

const getSelectedCategories = () =>
  [...document.querySelectorAll(".category-card.is-selected")].map(
    (card) => card.dataset.category,
  );

const showOnly = (screen) => {
  [welcomeScreen, categoryScreen, appScreen].forEach((item) => {
    item.classList.toggle("is-active", item === screen);
  });
};

const updateCategoryAction = () => {
  const selected = getSelectedCategories();

  if (currentStep !== "category") {
    return;
  }

  if (selected.length === 0) {
    startButton.disabled = true;
    startButton.textContent = "카테고리를 선택해 주세요";
    actionHelper.textContent = "하나 이상 선택하면 리포트를 만들 수 있어요.";
    return;
  }

  startButton.disabled = false;
  startButton.textContent = "내 리포트 만들기";
  actionHelper.textContent = `${selected.join(", ")} 중심으로 준비할게요.`;
};

const showWelcomeStep = () => {
  currentStep = "welcome";
  showOnly(welcomeScreen);
  appActions.hidden = false;
  bottomNav.hidden = true;
  startButton.disabled = false;
  startButton.textContent = "서비스 시작하기";
  actionHelper.textContent = "";
};

const showCategoryStep = () => {
  currentStep = "category";
  showOnly(categoryScreen);
  appActions.hidden = false;
  bottomNav.hidden = true;
  updateCategoryAction();
};

const animatePage = (page, animationName) => {
  if (!animationName) {
    return;
  }

  page.classList.remove("page-enter-soft", "page-enter-detail");
  void page.offsetWidth;
  page.classList.add(animationName);
};

const showAppPage = (pageName = "home", animationName = "page-enter-soft") => {
  currentStep = "app";
  showOnly(appScreen);
  appActions.hidden = true;
  bottomNav.hidden = false;

  appPages.forEach((page) => {
    const isTargetPage = page.dataset.page === pageName;
    page.classList.toggle("is-active", isTargetPage);

    if (isTargetPage) {
      animatePage(page, animationName);
    } else {
      page.classList.remove("page-enter-soft", "page-enter-detail");
    }
  });

  navItems.forEach((item) => {
    item.classList.toggle("is-active", item.dataset.target === pageName);
  });

  appScreen.style.padding = pageName === "chat" ? "0" : "";

  if (pageName === "home") {
    startHomeLoading();
  } else {
    clearHomeLoading();
  }

  if (pageName !== "detail") {
    resetInlineQuiz();
  }

  appScreen.scrollTop = 0;
};

const clearHomeLoading = () => {
  if (homeLoadingTimer) {
    clearTimeout(homeLoadingTimer);
    cancelAnimationFrame(homeLoadingTimer);
    homeLoadingTimer = null;
  }
};

const startHomeLoading = () => {
  const homePage = document.querySelector('[data-page="home"]');
  if (!homePage) return;

  clearHomeLoading();
  homePage.classList.remove("is-loaded");
  homePage.classList.add("is-loading");

  homePage.querySelectorAll(".loading-step").forEach((step) => {
    step.classList.remove("is-active", "is-done");
    const cur = step.querySelector("[data-cur]");
    const bar = step.querySelector(".loading-step-bar span");
    if (cur) cur.textContent = "0";
    if (bar) bar.style.width = "0%";
  });

  const stepEls = homePage.querySelectorAll(".loading-step");
  const plan = [
    { el: stepEls[0], total: 12, duration: 2200 },
    { el: stepEls[1], total: 8, duration: 2600 },
  ];

  let pi = 0;
  const runStep = () => {
    if (pi >= plan.length) {
      homePage.classList.remove("is-loading");
      homePage.classList.add("is-loaded");
      homeLoadingTimer = null;
      return;
    }
    const { el, total, duration } = plan[pi];
    if (!el) {
      pi += 1;
      runStep();
      return;
    }
    el.classList.add("is-active");
    const cur = el.querySelector("[data-cur]");
    const bar = el.querySelector(".loading-step-bar span");
    const start = performance.now();

    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const value = Math.min(total, Math.round(eased * total));
      if (cur) cur.textContent = String(value);
      if (bar) bar.style.width = (eased * 100).toFixed(1) + "%";
      if (t < 1) {
        homeLoadingTimer = requestAnimationFrame(tick);
      } else {
        if (cur) cur.textContent = String(total);
        if (bar) bar.style.width = "100%";
        el.classList.remove("is-active");
        el.classList.add("is-done");
        pi += 1;
        homeLoadingTimer = setTimeout(runStep, 240);
      }
    };
    homeLoadingTimer = requestAnimationFrame(tick);
  };
  runStep();
};

const renderQuizQuestion = () => {
  if (!inlineQuiz || !quizQuestion) {
    return;
  }

  const quizItem = detailQuizItems[currentQuizIndex];
  quizQuestionLabel.textContent = `Q${currentQuizIndex + 1}`;
  quizQuestion.textContent = quizItem.question;
  quizFeedback.hidden = true;
  quizNextButton.hidden = true;
  quizResultSummary.hidden = true;
  oxActions.hidden = false;
  quizNextButton.textContent =
    currentQuizIndex === detailQuizItems.length - 1 ? "결과 보기" : "다음 문제";

  quizStepDots.forEach((dot, index) => {
    dot.classList.toggle("is-active", index === currentQuizIndex);
    dot.classList.toggle("is-done", index < currentQuizIndex);
  });

  oxButtons.forEach((button) => {
    button.classList.remove("is-selected");
    button.disabled = false;
  });
};

const showQuizResult = () => {
  quizQuestionLabel.textContent = "Result";
  quizQuestion.textContent = `${detailQuizItems.length}문제 중 ${quizScore}문제를 맞혔어요.`;
  quizFeedback.hidden = true;
  quizNextButton.hidden = true;
  oxActions.hidden = true;

  oxButtons.forEach((button) => {
    button.classList.remove("is-selected");
    button.disabled = true;
  });

  quizStepDots.forEach((dot) => {
    dot.classList.add("is-done");
    dot.classList.remove("is-active");
  });

  const resultTone =
    quizScore === detailQuizItems.length
      ? "기사 핵심을 잘 잡았어요."
      : "틀린 문항의 해설만 다시 보면 흐름이 더 선명해져요.";

  quizResultSummary.innerHTML = `
    <p class="quiz-result-title">${resultTone}</p>
    <div class="quiz-result-list">
      ${detailQuizItems
        .map((item, index) => {
          const selectedAnswer = quizSelections[index] || "-";
          const isCorrect = selectedAnswer === item.answer;

          return `
            <div class="quiz-result-item">
              <span class="${isCorrect ? "is-correct" : "is-wrong"}">${isCorrect ? "O" : "X"}</span>
              <div>
                <strong>Q${index + 1}</strong>
                <p>${item.explanation}</p>
              </div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
  quizResultSummary.hidden = false;
};

startButton.addEventListener("click", () => {
  if (currentStep === "welcome") {
    showCategoryStep();
    history.pushState({ step: "category" }, "", "#category");
    return;
  }

  if (currentStep === "category") {
    showAppPage("home");
    history.pushState({ step: "app", page: "home" }, "", "#home");
  }
});

backButton.addEventListener("click", () => {
  if (currentStep === "category") {
    showWelcomeStep();
    history.pushState({ step: "welcome" }, "", location.pathname);
  }
});

categoryCards.forEach((card) => {
  card.addEventListener("click", () => {
    card.classList.toggle("is-selected");
    updateCategoryAction();
  });
});

navItems.forEach((item) => {
  item.addEventListener("click", () => {
    const targetPage = item.dataset.target;
    showAppPage(targetPage, "page-enter-soft");
    history.pushState({ step: "app", page: targetPage }, "", `#${targetPage}`);
  });
});

// ── 챗 플로우 ──
const chatIntro = document.querySelector("#chatIntro");
const chatMessages = document.querySelector("#chatMessages");
const chatInput = document.querySelector("#chatInput");
const chatSendBtn = document.querySelector("#chatSendBtn");
const chatBody = document.querySelector("#chatBody");

// 시안용 캔드 응답 맵
const CHAT_RESPONSES = {
  "어제 테크 뉴스 뭐 있었어?": {
    type: "articles",
    text: "어제 테크 관련 기사 2건을 찾았어요.",
    articles: [
      { cat: "테크", title: "구글 I/O 2025, Gemini 2.5 Pro 공개... 멀티모달 추론 강화", meta: "전자신문 · 어제 11:40" },
      { cat: "테크", title: "삼성전자, HBM4 개발 본격화... 엔비디아 공급 확대 기대", meta: "ZDNet Korea · 어제 09:15" },
    ],
  },
  "AI 관련 기사 찾아줘": {
    type: "articles",
    text: "최근 수집된 AI 관련 기사 2건을 찾았어요.",
    articles: [
      { cat: "테크", title: "오픈AI·앤트로픽, AI 에이전트 경쟁 본격화... 작업 자동화 시대 가시화", meta: "ZDNet Korea · 오늘 09:20" },
      { cat: "테크", title: "구글 I/O 2025, Gemini 2.5 Pro 공개... 멀티모달 추론 강화", meta: "전자신문 · 어제 11:40" },
    ],
  },
  "이번주 경제 흐름은?": {
    type: "text",
    text: "이번주 경제 흐름은 미국 관세 정책과 환율 변동이 핵심이었어요.\n\n반도체·자동차 수출 기업들이 관세 부담으로 압박을 받고 있고, 원달러 환율은 1,380원대에서 등락을 반복했어요.",
    source: true,
  },
  "오픈AI가 최근에 뭐 발표했어?": {
    type: "text",
    text: "오픈AI는 GPT-4o 업데이트와 함께 AI 에이전트 기능을 대폭 강화했어요. 이메일 전송, 파일 관리, 코드 실행 같은 실제 작업을 직접 처리할 수 있게 됐어요.",
    source: true,
  },
};

const DEFAULT_RESPONSE = {
  type: "text",
  text: "관련 기사를 찾고 있어요. 조금 더 구체적으로 말씀해 주시면 더 정확하게 찾아드릴 수 있어요.",
};

function scrollChatBottom() {
  if (chatBody) chatBody.scrollTop = chatBody.scrollHeight;
}

function makeBubble(role, content) {
  const row = document.createElement("div");
  row.className = `chat-msg chat-msg--${role} chat-msg--enter`;

  if (role === "user") {
    row.innerHTML = `<div class="chat-bubble chat-bubble--user">${content}</div>`;
  } else {
    row.innerHTML = `<span class="chat-ai-avatar" aria-hidden="true">AI</span><div class="chat-bubble chat-bubble--ai">${content}</div>`;
  }
  return row;
}

function makeTyping() {
  const row = document.createElement("div");
  row.className = "chat-msg chat-msg--ai chat-msg--enter";
  row.id = "chatTyping";
  row.innerHTML = `
    <span class="chat-ai-avatar" aria-hidden="true">AI</span>
    <div class="chat-bubble chat-bubble--ai chat-typing">
      <span></span><span></span><span></span>
    </div>`;
  return row;
}

function buildAIContent(response) {
  if (response.type === "articles") {
    const cards = response.articles
      .map(
        (a) => `
      <button class="chat-article-card" type="button">
        <span class="chat-article-cat">● ${a.cat}</span>
        <p class="chat-article-title">${a.title}</p>
        <span class="chat-article-meta">${a.meta}</span>
      </button>`
      )
      .join("");
    return `<p>${response.text}</p><div class="chat-article-cards">${cards}</div>`;
  }

  const lines = response.text
    .split("\n\n")
    .map((l) => `<p>${l}</p>`)
    .join("");
  const source = response.source
    ? `<div class="chat-source-label">
        <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
          <circle cx="7" cy="7" r="5.5"/><path d="M7 4.5v3l1.5 1.5"/>
        </svg>AI 요약 · 원문 기반</div>`
    : "";
  return lines + source;
}

function sendMessage(text) {
  if (!text.trim() || !chatMessages) return;

  // 인트로 숨김 (첫 메시지일 때만)
  if (chatIntro && !chatIntro.hidden) {
    chatIntro.hidden = true;
    chatMessages.hidden = false;
    if (chatResetBtn) chatResetBtn.hidden = false;
  }

  // 입력창 초기화
  if (chatInput) chatInput.value = "";

  // 사용자 버블
  chatMessages.appendChild(makeBubble("user", text));
  scrollChatBottom();

  // 타이핑 인디케이터
  const typing = makeTyping();
  chatMessages.appendChild(typing);
  scrollChatBottom();

  // AI 응답 (1초 딜레이)
  setTimeout(() => {
    typing.remove();
    const response = CHAT_RESPONSES[text] || DEFAULT_RESPONSE;
    chatMessages.appendChild(makeBubble("ai", buildAIContent(response)));
    scrollChatBottom();
  }, 1000);
}

document.querySelectorAll(".chat-suggestion-chip").forEach((chip) => {
  chip.addEventListener("click", () => sendMessage(chip.dataset.msg));
});

chatSendBtn?.addEventListener("click", () => sendMessage(chatInput?.value ?? ""));
chatInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage(chatInput.value);
});

const chatResetBtn = document.querySelector("#chatResetBtn");

function resetChat() {
  if (!chatMessages || !chatIntro) return;
  chatMessages.innerHTML = "";
  chatMessages.hidden = true;
  chatIntro.hidden = false;
  if (chatInput) chatInput.value = "";
  chatResetBtn.hidden = true;
}

chatResetBtn?.addEventListener("click", resetChat);

detailButtons.forEach((button) => {
  button.addEventListener("click", () => {
    showAppPage("detail", "page-enter-detail");
    history.pushState({ step: "app", page: "detail" }, "", "#detail");
  });
});

detailBackButton?.addEventListener("click", () => {
  showAppPage("home", "page-enter-soft");
  history.pushState({ step: "app", page: "home" }, "", "#home");
});

openInlineQuizButton?.addEventListener("click", () => {
  currentQuizIndex = 0;
  quizScore = 0;
  inlineQuiz.hidden = false;
  openInlineQuizButton.hidden = true;
  renderQuizQuestion();
  inlineQuiz.scrollIntoView({ behavior: "smooth", block: "start" });
});

oxButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const selectedAnswer = button.dataset.answer;
    const quizItem = detailQuizItems[currentQuizIndex];
    const isCorrect = selectedAnswer === quizItem.answer;

    if (isCorrect) {
      quizScore += 1;
    }

    quizSelections[currentQuizIndex] = selectedAnswer;

    oxButtons.forEach((item) => {
      item.classList.toggle("is-selected", item === button);
      item.disabled = true;
    });

    quizFeedbackTitle.textContent = isCorrect ? "맞았어요" : "조금 달라요";
    quizFeedbackText.textContent = quizItem.explanation;
    quizFeedback.hidden = false;
    quizNextButton.hidden = false;
    quizNextButton.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
});

quizNextButton?.addEventListener("click", () => {
  if (currentQuizIndex >= detailQuizItems.length - 1) {
    showQuizResult();
    return;
  }

  currentQuizIndex += 1;
  renderQuizQuestion();
});

window.addEventListener("popstate", () => {
  const hash = location.hash.replace("#", "");

  if (hash === "category") {
    showCategoryStep();
    return;
  }

  if (["home", "report", "detail"].includes(hash)) {
    showAppPage(hash);
    return;
  }

  showWelcomeStep();
});

const initialHash = location.hash.replace("#", "");

if (initialHash === "category") {
  showCategoryStep();
} else if (["home", "report", "detail"].includes(initialHash)) {
  showAppPage(initialHash);
} else {
  showWelcomeStep();
}
