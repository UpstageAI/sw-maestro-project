import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import Home from "../app/page";

test("renders_splash_page", () => {
  render(<Home />);

  expect(screen.getByRole("heading", { level: 1, name: "NewPick" })).toBeDefined();
  expect(
    screen.getByText("AI가 오늘의 뉴스를 골라 짧게 요약하고 퀴즈로 정리해요."),
  ).toBeDefined();
  expect(screen.getByRole("button", { name: "서비스 시작하기" })).toBeDefined();
  expect(screen.getByRole("img", { name: "NewPick logo" })).toBeDefined();
});
