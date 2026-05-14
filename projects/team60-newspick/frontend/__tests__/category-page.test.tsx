import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";
import CategoryPage from "../app/onboarding/category/page";
import { useCategoryStore } from "../lib/store/category";

beforeEach(() => {
  useCategoryStore.getState().reset();
});

test("renders_and_toggles_category_cards", () => {
  render(<CategoryPage />);

  expect(
    screen.getByRole("heading", { level: 1, name: "관심 있는 뉴스를 골라주세요" }),
  ).toBeDefined();
  expect(screen.getByRole("button", { name: "테크" })).toBeDefined();
  expect(screen.getByRole("button", { name: "경제" })).toBeDefined();
  expect(screen.getByRole("button", { name: "정책" })).toBeDefined();
  expect(screen.getByRole("button", { name: "이슈" })).toBeDefined();

  const techButton = screen.getByRole("button", { name: "테크" });
  const reportButton = screen.getByRole("button", { name: "내 리포트 만들기" });

  expect(techButton.getAttribute("aria-pressed")).toBe("true");
  expect(reportButton.getAttribute("href")).toBe("/feed?categories=tech&refresh=1");
  expect(screen.getByText("테크 중심으로 준비할게요.")).toBeDefined();

  fireEvent.click(techButton);

  expect(techButton.getAttribute("aria-pressed")).toBe("false");
  expect(
    screen.getByRole("button", { name: "카테고리를 선택해 주세요" }).hasAttribute("disabled"),
  ).toBe(true);
  expect(screen.getByText("하나 이상 선택하면 리포트를 만들 수 있어요.")).toBeDefined();
});
