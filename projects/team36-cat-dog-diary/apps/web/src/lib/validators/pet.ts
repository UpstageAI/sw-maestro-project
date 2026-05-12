import { z } from "zod";

const trimmed = (max: number) =>
  z
    .string()
    .transform((v) => v.trim())
    .pipe(z.string().min(1).max(max));

export const genderSchema = z.enum(["male", "female", "unknown"]);

export const createPetSchema = z.object({
  name: trimmed(20),
  species: trimmed(20),
  honorific: trimmed(20),
  gender: genderSchema,
});

export type CreatePetInput = z.infer<typeof createPetSchema>;

// Update — 전체 optional. partial이면 trim/길이 검증이 무력화되므로 직접 옵셔널 wrap.
export const updatePetSchema = z
  .object({
    name: trimmed(20).optional(),
    species: trimmed(20).optional(),
    honorific: trimmed(20).optional(),
    gender: genderSchema.optional(),
  })
  .refine((v) => Object.keys(v).length > 0, {
    message: "최소 한 필드를 수정해야 합니다",
  });

export type UpdatePetInput = z.infer<typeof updatePetSchema>;
