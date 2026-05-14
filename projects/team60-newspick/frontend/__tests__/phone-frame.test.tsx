import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PhoneFrame } from "../components/phone-frame";

describe("PhoneFrame", () => {
  it("renders_status_area_and_children", () => {
    render(
      <PhoneFrame>
        <p>프레임 안쪽 콘텐츠</p>
      </PhoneFrame>,
    );

    expect(screen.getByText("9:41")).toBeTruthy();
    expect(screen.getByText("5G 100%")).toBeTruthy();
    expect(screen.getByText("프레임 안쪽 콘텐츠")).toBeTruthy();
  });
});
