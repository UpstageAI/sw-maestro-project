import { requestRecommendations } from "../api/recommendations.js";
import { isAllowedPageUrl } from "../config.js";

const recommendButton = document.querySelector("#recommend-button");
const result = document.querySelector("#result");
const COURSE_HISTORY_LOAD_FAILED_MESSAGE = "수강 이력을 불러오지 못했습니다.";
const HISTORY_PAGE_URL = "https://www.swmaestro.ai/sw/mypage/userAnswer/history.do?menuNo=200047";

let currentPageContext = null;

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({
    active: true,
    currentWindow: true
  });

  return tab;
}

async function loadPageContext() {
  const tab = await getActiveTab();

  if (!tab?.id) {
    recommendButton.disabled = true;
    renderMessage("활성 탭 정보를 찾을 수 없습니다.", "");
    return;
  }

  const allowed = isAllowedPageUrl(tab.url);

  currentPageContext = {
    allowed,
    title: tab.title || "제목 없는 페이지",
    url: tab.url,
    courseHistories: []
  };

  if (!allowed) {
    recommendButton.disabled = true;
    renderUnsupportedPageMessage();
    return;
  }

  recommendButton.disabled = false;
  renderMessage(
    "추천 준비 완료",
    "추천 받기를 누르면 현재 페이지의 수강 이력을 스크래핑한 뒤 추천을 요청합니다."
  );
}

recommendButton.addEventListener("click", async () => {
  recommendButton.disabled = true;
  result.hidden = false;

  try {
    recommendButton.textContent = "수강 이력 스크래핑 중...";
    renderLoadingMessage(
      "수강 이력 스크래핑 중",
      "현재 페이지와 접수내역 페이지들을 확인하고 있습니다."
    );
    const tab = await getActiveTab();
    const pageContext = await scrapePageContext(tab);
    const histories = createHistoriesFromPageContext(pageContext);

    currentPageContext = pageContext;
    recommendButton.textContent = "추천 요청 중...";
    renderRecommendationRequestMessage(histories);

    const recommendation = await requestRecommendations({
      histories,
      limit: 10
    });

    renderRecommendationResult(recommendation, histories);
  } catch (error) {
    renderError(error);
  } finally {
    recommendButton.disabled = !currentPageContext?.allowed;
    recommendButton.textContent = "추천 받기";
  }
});

loadPageContext().catch(() => {
  recommendButton.disabled = true;
  renderMessage("현재 페이지 정보를 불러오지 못했습니다.", "");
});

async function scrapePageContext(tab) {
  if (!tab?.id) {
    throw new Error("활성 탭 정보를 찾을 수 없습니다.");
  }

  const response = await getPageContextFromContentScript(tab);
  const url = response?.url || tab.url;
  const allowed = response?.allowed ?? isAllowedPageUrl(url);

  if (!allowed) {
    return {
      allowed: false,
      title: response?.title || tab.title || "제목 없는 페이지",
      url,
      courseHistories: []
    };
  }

  if (!response) {
    throw createContentScriptCommunicationError(tab, "스크래핑 응답이 비어 있습니다.");
  }

  return {
    allowed,
    title: response.title || tab.title || "제목 없는 페이지",
    body: response.body,
    url,
    courseHistories: response.courseHistories || [],
    scrapeError: response.scrapeError,
    scrapeStatus: response.scrapeStatus
  };
}

async function getPageContextFromContentScript(tab) {
  try {
    return await requestPageContext(tab);
  } catch (firstError) {
    try {
      await injectContentScript(tab);
      return await requestPageContext(tab);
    } catch (secondError) {
      throw createContentScriptCommunicationError(
        tab,
        "콘텐츠 스크립트 자동 주입 후에도 통신하지 못했습니다.",
        [firstError.message, secondError.message]
      );
    }
  }
}

async function requestPageContext(tab) {
  return await chrome.tabs.sendMessage(tab.id, {
    type: "GET_PAGE_CONTEXT"
  });
}

async function injectContentScript(tab) {
  await chrome.scripting.executeScript({
    target: {
      tabId: tab.id
    },
    files: ["src/content.js"]
  });
}

function createContentScriptCommunicationError(tab, reason, causes = []) {
  const runtimeError = chrome.runtime?.lastError?.message;
  const details = [
    `탭 ID: ${tab?.id || "없음"}`,
    `탭 URL: ${tab?.url || "없음"}`,
    `원인: ${reason || runtimeError || "알 수 없는 통신 오류"}`,
    ...causes.filter(Boolean).map((cause) => `세부 원인: ${cause}`),
    "확장 프로그램을 새로고침한 뒤 SW Maestro 페이지도 다시 새로고침해 주세요.",
    "주소가 /sw/mypage/userAnswer/history.do?menuNo=200047 형태인지 확인해 주세요."
  ];
  const error = new Error("페이지 스크래핑 스크립트와 통신하지 못했습니다.");

  error.code = "CONTENT_SCRIPT_COMMUNICATION_FAILED";
  error.details = details;

  return error;
}

function createHistoriesFromPageContext(pageContext) {
  if (!pageContext?.url) {
    throw new Error("추천 요청에 사용할 페이지 URL이 없습니다.");
  }

  if (!pageContext.allowed) {
    throw new Error("설정된 URL에서만 추천을 요청할 수 있습니다.");
  }

  if (pageContext.scrapeError) {
    throw new Error(pageContext.scrapeError);
  }

  if (pageContext.courseHistories?.length > 0) {
    return pageContext.courseHistories;
  }

  throw new Error(COURSE_HISTORY_LOAD_FAILED_MESSAGE);
}

function renderRecommendationResult(recommendation, histories = []) {
  const items = recommendation.items || [];

  if (items.length === 0) {
    result.innerHTML = `
      <p class="result-title">추천 결과가 없습니다.</p>
      <p class="result-meta">${escapeHtml(recommendation.interest_summary || "관심사 요약이 없습니다.")}</p>
      ${renderScrapedHistoryDetails(histories)}
    `;
    return;
  }

  result.innerHTML = `
    <p class="result-title">추천 결과 ${items.length}개</p>
    <p class="result-meta">${escapeHtml(recommendation.interest_summary)}</p>
    <ul class="recommendation-list">
      ${items.map(renderRecommendationItem).join("")}
    </ul>
    ${renderScrapedHistoryDetails(histories)}
  `;
}

function renderRecommendationItem(item) {
  return `
    <li class="recommendation-item">
      <a href="${escapeAttribute(item.url)}" target="_blank" rel="noreferrer">
        ${escapeHtml(item.title)}
      </a>
      <p>${escapeHtml(item.summary)}</p>
      <p class="reason">${escapeHtml(item.reason)}</p>
    </li>
  `;
}

function renderMessage(title, message) {
  result.hidden = false;
  result.innerHTML = `
    <p class="result-title">${escapeHtml(title)}</p>
    ${message ? `<p class="result-meta">${escapeHtml(message)}</p>` : ""}
  `;
}

function renderLoadingMessage(title, message) {
  result.hidden = false;
  result.innerHTML = `
    ${renderLoadingHeader(title)}
    ${message ? `<p class="result-meta">${escapeHtml(message)}</p>` : ""}
  `;
}

function renderUnsupportedPageMessage() {
  result.hidden = false;
  result.innerHTML = `
    <p class="result-title">추천할 수 없는 페이지입니다.</p>
    <p class="result-meta">SW 마에스트로 접수내역 페이지에서 수강 이력을 기반으로 추천을 받을 수 있습니다.</p>
    <a class="page-link" href="${escapeAttribute(HISTORY_PAGE_URL)}" target="_blank" rel="noreferrer">
      접수내역 페이지로 이동
    </a>
  `;
}

function renderRecommendationRequestMessage(histories) {
  result.hidden = false;
  result.innerHTML = `
    ${renderLoadingHeader("추천 요청 중")}
    <p class="result-meta">${histories.length}개의 수강 이력을 기반으로 추천을 요청하고 있습니다.</p>
    ${renderScrapedHistoryDetails(histories, true)}
  `;
}

function renderLoadingHeader(title) {
  return `
    <div class="loading-header" role="status" aria-live="polite">
      <span class="loading-spinner" aria-hidden="true"></span>
      <p class="result-title">${escapeHtml(title)}<span class="loading-dots" aria-hidden="true"></span></p>
    </div>
  `;
}

function renderScrapedHistoryDetails(histories, open = false) {
  if (!histories.length) {
    return "";
  }

  const carouselItems = [...histories, ...histories];

  return `
    <section class="scraped-history" aria-label="스크래핑된 수강 이력">
      <div class="scraped-history-header">
        <p>사용자의 수강 이력 ${histories.length}개</p>
        <span>${open ? "나의 수강 이력" : "추천에 사용된 이력"}</span>
      </div>
      <div class="scraped-history-carousel">
        <ol class="scraped-history-list">
          ${carouselItems.map((history, index) => renderScrapedHistoryItem(history, index >= histories.length)).join("")}
        </ol>
      </div>
    </section>
  `;
}

function renderScrapedHistoryItem(history, duplicated = false) {
  const title = history.title || "제목 없음";
  const mentor = history.mentor || "-";
  const takenAt = history.taken_at || "-";
  const body = history.body || "상세 내용이 없습니다.";

  return `
    <li ${duplicated ? 'aria-hidden="true"' : ""}>
      <details class="scraped-history-item">
        <summary>
          <span class="scraped-history-title">${escapeHtml(title)}</span>
          <span class="scraped-history-preview">${escapeHtml(body)}</span>
        </summary>
        <div class="scraped-history-body">
          <a href="${escapeAttribute(history.url || "#")}" target="_blank" rel="noreferrer">
            원본 페이지 열기
          </a>
          <p>멘토: ${escapeHtml(mentor)}</p>
          <p>기준 시각: ${escapeHtml(takenAt)}</p>
          <pre>${escapeHtml(body)}</pre>
        </div>
      </details>
    </li>
  `;
}

function renderError(error) {
  result.innerHTML = `
    <p class="result-title">추천 요청에 실패했습니다.</p>
    <p class="result-meta">${escapeHtml(error.message)}</p>
    ${error.code ? `<p class="result-code">${escapeHtml(error.code)}</p>` : ""}
    ${renderErrorDetails(error)}
  `;
}

function renderErrorDetails(error) {
  if (!error.details?.length) {
    return "";
  }

  return `
    <ul class="result-details">
      ${error.details.map((detail) => `<li>${escapeHtml(detail)}</li>`).join("")}
    </ul>
  `;
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value = "") {
  return escapeHtml(value);
}
