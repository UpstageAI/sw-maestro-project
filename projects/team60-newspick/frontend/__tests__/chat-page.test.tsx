import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ChatPage from "../app/(app)/chat/page";

describe("ChatPage", () => {
  it("chat_page_uses_smooth_enter_animation", () => {
    render(<ChatPage />);

    expect(screen.getByTestId("chat-page").className).toContain("page-enter-chat");
  });
});
