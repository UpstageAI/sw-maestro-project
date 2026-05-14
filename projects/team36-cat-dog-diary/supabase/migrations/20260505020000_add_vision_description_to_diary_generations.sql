-- diary_generations에 vision_description 컬럼 추가.
-- 후속: regenerate(seq>=2) 시 BFF가 lastGen.vision_description을 SELECT해서
-- gateway에 forward하고, ai-gateway graph가 conditional edge로 vision LLM
-- 호출을 skip한다. 기존 row는 NULL — 다음 regenerate에서 self-heal.

ALTER TABLE "public"."diary_generations"
  ADD COLUMN IF NOT EXISTS "vision_description" text;

ALTER TABLE "public"."diary_generations"
  ADD CONSTRAINT "diary_generations_vision_description_check"
    CHECK (
      ("vision_description" IS NULL)
      OR (
        ("length"("vision_description") >= 1)
        AND ("length"("vision_description") <= 1000)
      )
    );
