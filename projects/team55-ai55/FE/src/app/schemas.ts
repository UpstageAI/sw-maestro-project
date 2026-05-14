import { z } from "zod";

export const backendIdSchemas = {
  evt: z.string().regex(/^evt_[A-Za-z0-9]{8,}$/),
  mem: z.string().regex(/^mem_[A-Za-z0-9]{6,}$/),
  ms: z.string().regex(/^ms_[A-Za-z0-9]{6,}$/),
  proj: z.string().regex(/^proj_[A-Za-z0-9]{8,}$/),
  task: z.string().regex(/^task_[A-Za-z0-9]{8,}$/),
};

export const localStoreEnvelopeSchema = z
  .object({
    schemaVersion: z.literal(1),
    currentUser: z.object({ name: z.string() }).nullable().optional(),
    projects: z.array(z.object({ id: z.string() }).passthrough()),
    clientMetrics: z
      .object({
        analyzeLatenciesMs: z.array(z.unknown()).optional(),
        suggestionAcceptanceEvents: z.array(z.unknown()).optional(),
      })
      .partial()
      .optional(),
  })
  .passthrough();

export const taskDraftSchema = z
  .object({
    title: z.string().trim().min(1),
    progress: z.number().min(0).max(100),
    estimatedHours: z.number().positive().nullable().optional(),
  })
  .passthrough();
