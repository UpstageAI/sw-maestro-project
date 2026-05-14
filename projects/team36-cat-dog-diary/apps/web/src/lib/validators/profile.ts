import { z } from "zod";

const trimmed = (max: number) =>
  z
    .string()
    .transform((v) => v.trim())
    .pipe(z.string().min(1).max(max));

export const updateProfileSchema = z.object({
  display_name: trimmed(24),
});

export type UpdateProfileInput = z.infer<typeof updateProfileSchema>;
