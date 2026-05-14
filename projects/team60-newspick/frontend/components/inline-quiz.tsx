"use client";

import { useEffect, useRef, useState } from "react";

type QuizAnswer = "O" | "X";

export type InlineQuizItem = {
  id: string;
  question: string;
  answer: boolean | QuizAnswer;
  explanation: string;
};

type InlineQuizProps = {
  quiz: InlineQuizItem | InlineQuizItem[];
};

function getCorrectAnswer(answer: InlineQuizItem["answer"]): QuizAnswer {
  return answer === true || answer === "O" ? "O" : "X";
}

export function InlineQuiz({ quiz }: InlineQuizProps) {
  const quizzes = Array.isArray(quiz) ? quiz : [quiz];
  const currentQuiz = quizzes[0];
  const [selectedAnswer, setSelectedAnswer] = useState<QuizAnswer | null>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const isAnswered = selectedAnswer !== null;

  useEffect(() => {
    if (!isAnswered || !feedbackRef.current) {
      return;
    }

    const shouldReduceMotion =
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    feedbackRef.current.scrollIntoView?.({
      behavior: shouldReduceMotion ? "auto" : "smooth",
      block: "nearest",
    });
  }, [isAnswered]);

  if (!currentQuiz) {
    return null;
  }

  const questionId = `${currentQuiz.id}-question`;
  const correctAnswer = getCorrectAnswer(currentQuiz.answer);
  const isCorrect = selectedAnswer === correctAnswer;

  const getAnswerButtonClassName = (answer: QuizAnswer) =>
    [
      "grid min-h-[58px] place-items-center rounded-[18px] border text-[22px] font-[850] shadow-[0_8px_18px_rgba(25,31,40,0.04)] transition-[transform,border-color,background-color,color,box-shadow] duration-200 ease-out active:translate-y-[2px] disabled:cursor-default disabled:opacity-100",
      selectedAnswer === answer
        ? "border-[rgba(255,138,61,0.34)] bg-brand-50 text-brand-500 shadow-[0_10px_20px_rgba(255,138,61,0.16)]"
        : "border-line bg-white text-ink",
    ].join(" ");

  return (
    <section
      aria-label="기사 이해도 OX 퀴즈"
      className="grid gap-4 rounded-[24px] border border-[rgba(255,138,61,0.24)] bg-[linear-gradient(180deg,#fff7f1_0%,#ffffff_72%)] p-5 shadow-[0_12px_30px_rgba(25,31,40,0.06)]"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[13px] font-[900] leading-normal text-brand-500">
            읽은 내용 확인하기
          </p>
          <small className="mt-[5px] block text-[12px] font-[700] leading-[1.35] text-hint">
            기사 핵심을 가볍게 체크해볼게요.
          </small>
        </div>
        <span className="rounded-full bg-brand-50 px-2.5 py-1 text-[11px] font-[900] leading-none text-brand-500">
          OX
        </span>
      </div>

      <strong
        id={questionId}
        role="heading"
        aria-level={3}
        className="break-keep text-[15px] font-[750] leading-[1.6] text-ink"
      >
        {currentQuiz.question}
      </strong>

      <div aria-label="O 또는 X 선택" className="grid grid-cols-2 gap-[11px]">
        <button
          type="button"
          aria-describedby={questionId}
          aria-pressed={selectedAnswer === "O"}
          disabled={isAnswered}
          onClick={() => setSelectedAnswer("O")}
          className={getAnswerButtonClassName("O")}
        >
          O
        </button>
        <button
          type="button"
          aria-describedby={questionId}
          aria-pressed={selectedAnswer === "X"}
          disabled={isAnswered}
          onClick={() => setSelectedAnswer("X")}
          className={getAnswerButtonClassName("X")}
        >
          X
        </button>
      </div>

      {isAnswered ? (
        <div
          ref={feedbackRef}
          role="status"
          className="quiz-feedback-enter grid gap-1.5 overflow-hidden rounded-2xl bg-[#f8fafb] p-3.5"
        >
          <div className="flex flex-wrap items-center gap-2">
            <strong className="text-[14px] font-[900] text-ink">
              {isCorrect ? "정답입니다" : "아쉽습니다"}
            </strong>
            <span className="rounded-full bg-white px-2 py-1 text-[11px] font-[850] text-muted">
              정답 {correctAnswer}
            </span>
          </div>
          <p className="m-0 max-w-none break-keep text-[13px] font-[650] leading-[1.5] text-muted">
            {currentQuiz.explanation}
          </p>
        </div>
      ) : null}
    </section>
  );
}
