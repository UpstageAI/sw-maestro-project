import fs from "node:fs";

async function runReview() {
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    console.error(
      "🚨 에러: GEMINI_API_KEY 환경 변수가 없습니다. GitHub Secrets를 확인해주세요.",
    );
    process.exit(1);
  }

  const prDiff = fs.readFileSync("pr_diff.txt", "utf-8");
  const styleGuide = fs.readFileSync(".github/styleguide.md", "utf-8");

  if (!prDiff.trim()) {
    console.log("변경된 코드가 없어 리뷰를 생략합니다.");
    return;
  }

  const prompt = `
    당신은 시니어 프론트엔드 개발자입니다. 다음 스타일 가이드를 엄격히 지켜서 아래 변경된 코드를 리뷰해주세요.
    
    [스타일 가이드]
    ${styleGuide}
    
    [변경된 코드 (Git Diff)]
    ${prDiff}
  `;

  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
      }),
    },
  );

  const data = await response.json();

  // 💡 [추가된 부분] API 응답이 실패했을 때 에러 내용을 상세히 출력
  if (!response.ok || !data.candidates) {
    console.error("🚨 제미나이 API 호출 실패!");
    console.error("상태 코드:", response.status);
    console.error("상세 에러 내용:", JSON.stringify(data, null, 2));
    process.exit(1); // 강제 종료하여 Actions 실패(빨간불) 처리
  }

  const reviewComment = data.candidates[0].content.parts[0].text;
  fs.writeFileSync("review_result.txt", reviewComment);
}

runReview().catch((error) => {
  console.error("🚨 스크립트 실행 중 예기치 못한 에러 발생:", error);
  process.exit(1);
});
