import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

// Portfolio entries: one Markdown file per project in src/content/work/.
// The file name becomes the URL: src/content/work/my-project.md -> /work/my-project/
const work = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/work' }),
  schema: ({ image }) =>
    z.object({
      title: z.string(),
      summary: z.string(),
      year: z.number(),
      role: z.string().optional(),
      tags: z.array(z.string()).default([]),
      cover: image().optional(),
      link: z.string().url().optional(),
      // Lower numbers come first; ties fall back to newest year.
      order: z.number().default(100),
      // Drafts are visible with `npm run dev` but never published.
      draft: z.boolean().default(false),
    }),
});

export const collections = { work };
