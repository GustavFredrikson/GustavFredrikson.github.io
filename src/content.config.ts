import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

// Portfolio entries: add a Markdown file to src/content/work/ and it shows up on the home page.
const work = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/work' }),
  schema: z.object({
    title: z.string(),
    summary: z.string(),
    year: z.number(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { work };
