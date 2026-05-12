import { z } from 'zod';

export const chefRecipeSchema = z.object({
	recipeTitle: z.string().default(''),
	targetIssues: z.array(z.string()).default([]),
	ingredients: z.array(z.string()).default([]),
	steps: z.array(z.string()).default([]),
	operationalNotes: z.array(z.string()).default([]),
	expectedImprovements: z.array(z.string()).default([])
});

export type ChefRecipe = z.infer<typeof chefRecipeSchema>;
