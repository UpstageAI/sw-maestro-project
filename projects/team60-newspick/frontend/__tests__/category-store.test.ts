import { beforeEach, expect, test } from "vitest";
import { useCategoryStore } from "../lib/store/category";

beforeEach(() => {
  useCategoryStore.getState().reset();
});

test("toggle_category_updates_selected_categories", () => {
  expect(useCategoryStore.getState().selected).toEqual(["tech"]);

  useCategoryStore.getState().toggle("tech");

  expect(useCategoryStore.getState().selected).toEqual([]);

  useCategoryStore.getState().toggle("tech");

  expect(useCategoryStore.getState().selected).toEqual(["tech"]);
});
