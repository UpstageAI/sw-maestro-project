import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import { useCategoryStore } from "../lib/store/category";
import { useChatStore } from "../lib/store/chat";
import { useRefreshStore } from "../lib/store/refresh";

afterEach(() => {
  cleanup();
  useCategoryStore.getState().reset();
  useChatStore.getState().reset();
  useRefreshStore.getState().reset();
  localStorage.clear();
});
