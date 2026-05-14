import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InlineQuiz } from "../components/inline-quiz";

const quiz = {
  id: "quiz_001",
  question: "AI 기술은 기사 작성 시간을 줄이고 검수 품질을 높인다.",
  answer: true,
  explanation: "본문에서 AI가 작성 시간을 줄이고 검수 품질을 높였다고 설명했어요.",
};

describe("InlineQuiz", () => {
  it("inline_quiz_renders_single_question_and_ox_buttons", () => {
    render(<InlineQuiz quiz={quiz} />);

    expect(
      screen.getByRole("heading", {
        name: /AI 기술은 기사 작성 시간을 줄이고 검수 품질을 높인다/,
      }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "O" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "X" })).toBeTruthy();
    expect(screen.queryByText("Q1")).toBeNull();
    expect(screen.queryByText("1 / 1")).toBeNull();
    expect(screen.queryByRole("button", { name: "결과 보기" })).toBeNull();
    expect(screen.queryByText("정답입니다")).toBeNull();
    expect(screen.queryByText("아쉽습니다")).toBeNull();
  });

  it("selecting_correct_answer_shows_success_feedback_and_explanation", () => {
    render(<InlineQuiz quiz={quiz} />);

    const correctButton = screen.getByRole("button", { name: "O" });
    const wrongButton = screen.getByRole("button", { name: "X" });

    fireEvent.click(correctButton);

    const status = screen.getByRole("status");

    expect(status.className).toContain("bg-[#f8fafb]");
    expect(status.className).toContain("rounded-2xl");
    expect(status.className).toContain("quiz-feedback-enter");
    expect(screen.getByText("정답입니다")).toBeTruthy();
    expect(screen.getByText("정답 O")).toBeTruthy();
    expect(screen.getByText("본문에서 AI가 작성 시간을 줄이고 검수 품질을 높였다고 설명했어요.")).toBeTruthy();
    expect(correctButton.getAttribute("aria-pressed")).toBe("true");
    expect(wrongButton.hasAttribute("disabled")).toBe(true);
    expect(screen.queryByRole("button", { name: "결과 보기" })).toBeNull();
  });

  it("selecting_wrong_answer_shows_wrong_feedback_and_correct_answer", () => {
    render(<InlineQuiz quiz={quiz} />);

    const correctButton = screen.getByRole("button", { name: "O" });
    const wrongButton = screen.getByRole("button", { name: "X" });

    fireEvent.click(wrongButton);

    expect(screen.getByText("아쉽습니다")).toBeTruthy();
    expect(screen.getByText("정답 O")).toBeTruthy();
    expect(screen.getByText("본문에서 AI가 작성 시간을 줄이고 검수 품질을 높였다고 설명했어요.")).toBeTruthy();
    expect(wrongButton.getAttribute("aria-pressed")).toBe("true");
    expect(correctButton.hasAttribute("disabled")).toBe(true);
  });

  it("inline_quiz_uses_first_question_without_multi_step_flow", () => {
    render(
      <InlineQuiz
        quiz={[
          {
            ...quiz,
            id: "quiz_001",
            question: "첫 번째 질문",
          },
          {
            ...quiz,
            id: "quiz_002",
            question: "두 번째 질문",
          },
        ]}
      />,
    );

    expect(screen.getByRole("heading", { name: "첫 번째 질문" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "두 번째 질문" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "O" }));

    expect(screen.queryByRole("button", { name: "다음 문항" })).toBeNull();
    expect(screen.queryByRole("button", { name: "결과 보기" })).toBeNull();
  });
});
