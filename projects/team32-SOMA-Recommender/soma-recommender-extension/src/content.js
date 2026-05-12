const HISTORY_HOSTS = ["www.swmaestro.ai", "swmaestro.ai"];
const HISTORY_PATH = "/sw/mypage/userAnswer/history.do";
const HISTORY_MENU_NO = "200047";
const MAX_HISTORY_PAGES = 20;

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "GET_PAGE_CONTEXT") {
    return;
  }

  buildPageContext()
    .then(sendResponse)
    .catch((error) => {
      sendResponse({
        allowed: isAllowedPageUrl(window.location.href),
        title: document.title,
        body: getText(document.body).slice(0, 2000),
        url: window.location.href,
        courseHistories: [],
        scrapeError: error.message,
        scrapeStatus: "failed"
      });
    });

  return true;
});

async function buildPageContext() {
  const url = window.location.href;

  if (!isAllowedPageUrl(url)) {
    return {
      allowed: false,
      title: document.title,
      url,
      courseHistories: []
    };
  }

  const scrapedHistories = await scrapeAllHistoryPages(document, url);

  return {
    allowed: true,
    title: document.title,
    body: getText(document.body).slice(0, 2000),
    url,
    courseHistories: scrapedHistories,
    scrapeStatus: "success"
  };
}

async function scrapeAllHistoryPages(currentDocument, currentUrl) {
  const pageUrls = getHistoryPageUrls(currentDocument, currentUrl);
  const histories = [];

  for (const pageUrl of pageUrls) {
    const pageDocument = isSameUrl(pageUrl, currentUrl)
      ? currentDocument
      : await fetchHistoryDocument(pageUrl);
    histories.push(...scrapeHistoryDocument(pageDocument, pageUrl));
  }

  return dedupeHistories(histories);
}

async function fetchHistoryDocument(url) {
  const response = await fetch(url, {
    credentials: "include"
  });

  if (!response.ok) {
    throw new Error(`Failed to load history page. Status code: ${response.status}`);
  }

  const html = await response.text();
  return new DOMParser().parseFromString(html, "text/html");
}

function getHistoryPageUrls(doc, currentUrl) {
  const current = new URL(currentUrl);
  const endPage = getEndPage(doc);
  const urls = [];

  for (let pageIndex = 1; pageIndex <= endPage; pageIndex += 1) {
    const url = new URL(current.href);
    url.searchParams.set("menuNo", HISTORY_MENU_NO);
    url.searchParams.set("pageIndex", String(pageIndex));
    urls.push(url.href);
  }

  return urls.slice(0, MAX_HISTORY_PAGES);
}

function getEndPage(doc) {
  const endPageValue = doc.querySelector(".paginationSet [data-endpage]")?.dataset.endpage;
  const endPage = Number.parseInt(endPageValue || "", 10);

  if (Number.isInteger(endPage) && endPage > 0) {
    return endPage;
  }

  const pageIndexes = [...doc.querySelectorAll(".paginationSet a[href*='pageIndex=']")]
    .map((anchor) =>
      Number.parseInt(
        new URL(anchor.getAttribute("href"), window.location.href).searchParams.get("pageIndex") ||
          "",
        10
      )
    )
    .filter((pageIndex) => Number.isInteger(pageIndex) && pageIndex > 0);

  return Math.max(1, ...pageIndexes);
}

function scrapeHistoryDocument(doc, pageUrl) {
  const table = doc.querySelector(".boardlist .tbl-ovx table");

  if (!table) {
    return [];
  }

  return [...table.querySelectorAll("tbody tr")]
    .map((row) => scrapeHistoryRow(row, pageUrl))
    .filter(Boolean);
}

function scrapeHistoryRow(row, pageUrl) {
  const cells = [...row.querySelectorAll("td")];

  if (cells.length < 10) {
    return null;
  }

  const no = getText(cells[0]);
  const type = getText(cells[1]);
  const titleLink = cells[2].querySelector("a[href]");
  const title = getText(titleLink || cells[2]);
  const mentor = getText(cells[3]);
  const lectureDate = getText(cells[4]);
  const registeredAt = getText(cells[5]);
  const status = getText(cells[6]);
  const approval = getText(cells[7]);
  const answerHistory = getText(cells[8]);
  const note = getText(cells[9]);

  if (!title) {
    return null;
  }

  return {
    url: titleLink
      ? new URL(titleLink.getAttribute("href"), pageUrl).href
      : `${pageUrl}#history-${no || title}`,
    title: type ? `[${type}] ${title}` : title,
    body: createHistoryBody({
      type,
      title,
      mentor,
      lectureDate,
      registeredAt,
      status,
      approval,
      answerHistory,
      note
    }),
    mentor,
    taken_at: parseDateTime(registeredAt) || new Date().toISOString()
  };
}

function createHistoryBody(history) {
  return [
    ["\uad6c\ubd84", history.type],
    ["\uc81c\ubaa9", history.title],
    ["\uc791\uc131\uc790", history.mentor],
    ["\uac15\uc758\ub0a0\uc9dc", history.lectureDate],
    ["\uc811\uc218\uc77c", history.registeredAt],
    ["\uc811\uc218\uc0c1\ud0dc", history.status],
    ["\uac1c\uc124\uc2b9\uc778", history.approval],
    ["\uc811\uc218\ub0b4\uc5ed", history.answerHistory],
    ["\ube44\uace0", history.note]
  ]
    .filter(([, value]) => value && value !== "-")
    .map(([label, value]) => `${label}: ${value}`)
    .join("\n");
}

function parseDateTime(value = "") {
  const normalized = normalizeText(value);
  const match = normalized.match(
    /(?<year>\d{4})-(?<month>\d{1,2})-(?<day>\d{1,2})(?:\s+(?<hour>\d{1,2}):(?<minute>\d{1,2}))?/
  );

  if (!match?.groups) {
    return null;
  }

  const { year, month, day, hour = "0", minute = "0" } = match.groups;
  const date = new Date(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute));

  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function dedupeHistories(histories) {
  const uniqueHistories = [];
  const seenUrls = new Set();

  for (const history of histories) {
    if (!history.url || seenUrls.has(history.url)) {
      continue;
    }

    seenUrls.add(history.url);
    uniqueHistories.push(history);
  }

  return uniqueHistories;
}

function isAllowedPageUrl(url) {
  try {
    const parsedUrl = new URL(url);
    return (
      HISTORY_HOSTS.includes(parsedUrl.hostname) &&
      parsedUrl.pathname === HISTORY_PATH &&
      parsedUrl.searchParams.get("menuNo") === HISTORY_MENU_NO
    );
  } catch {
    return false;
  }
}

function isSameUrl(left, right) {
  const leftUrl = new URL(left);
  const rightUrl = new URL(right);
  return leftUrl.href === rightUrl.href;
}

function getText(element) {
  return normalizeText(element?.textContent || "");
}

function normalizeText(value = "") {
  return String(value).replace(/\s+/g, " ").trim();
}
