import { z } from "zod";

const uuid = z.string().uuid();
const keywords = z.string().min(1).max(1000);

export const generateSchema = z.object({
  pet_id: uuid,
  photo_path: z.string().min(1).max(512),
  keywords,
});
export type GenerateInput = z.infer<typeof generateSchema>;

export const regenerateSchema = z.object({
  session_id: uuid,
  pet_id: uuid,
  photo_path: z.string().min(1).max(512),
  keywords,
  feedback: z.string().min(1).max(500).optional(),
});
export type RegenerateInput = z.infer<typeof regenerateSchema>;

export const adoptSchema = z.object({
  source_generation_id: uuid,
});
export type AdoptInput = z.infer<typeof adoptSchema>;
