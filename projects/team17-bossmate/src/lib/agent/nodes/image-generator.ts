import { generateAzureImage } from "../../image-gen";
import type { PromotionStateType } from "../state";

export async function imageGenerator(state: PromotionStateType) {
  if (!state.copy) {
    return {
      agentTrace: [
        {
          step: "ImageGenerator",
          summary: "문구 정보가 없어 카드 이미지를 만들 수 없어요.",
        },
      ],
    };
  }

  const productImage = state.request.productImage;
  const result = await generateAzureImage(state.copy.imagePrompt, {
    productImage,
  });
  if (result) {
    return {
      image: { dataUrl: result.dataUrl, source: "azure" as const },
      agentTrace: [
        {
          step: "ImageGenerator",
          summary: productImage
            ? "올려주신 제품 사진을 참고해 카드 이미지를 만들었어요."
            : "카드 이미지를 만들었어요.",
        },
      ],
    };
  }

  return {
    agentTrace: [
      {
        step: "ImageGenerator",
        summary: "이미지 생성에 실패해 임시 디자인으로 대체했어요.",
      },
    ],
  };
}
