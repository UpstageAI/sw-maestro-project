import { HttpResponse, delay, http } from "msw";
import { articleDetails, feedArticles } from "./fixtures/articles";
import { dailyReports } from "./fixtures/reports";

export const handlers = [
  http.get("*/api/feed", async () => {
    await delay(3000);
    return HttpResponse.json({
      articles: feedArticles,
    });
  }),
  http.get("*/api/articles/:articleId", async ({ params }) => {
    await delay(500);
    const articleId = String(params.articleId);
    const article = articleDetails[articleId];

    if (!article) {
      return HttpResponse.json(
        { code: "ARTICLE_NOT_FOUND", message: "기사를 찾을 수 없습니다" },
        { status: 404 },
      );
    }

    return HttpResponse.json(article);
  }),
  http.get("*/api/report/:date", ({ params }) => {
    const date = String(params.date);
    const report = dailyReports[date];

    if (!report) {
      return HttpResponse.json({ code: "REPORT_NOT_READY", date }, { status: 404 });
    }

    return HttpResponse.json(report);
  }),
  http.get("*/api/refresh-stream", () => {
    const body = [
      'event: step\ndata: {"step":"collect","current":0,"total":12}\n',
      'event: step\ndata: {"step":"collect","current":12,"total":12}\n',
      'event: step\ndata: {"step":"summarize","current":8,"total":8}\n',
      'event: done\ndata: {"articleIds":[]}\n',
    ].join("\n");

    return new Response(body, {
      headers: {
        "Content-Type": "text/event-stream",
      },
    });
  }),
];
