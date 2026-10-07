import { defineCollection } from 'astro:content';
import { file, glob } from 'astro/loaders';
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
      // Optional variant shown when the visitor's system is in dark mode.
      coverDark: image().optional(),
      link: z.string().url().optional(),
      // Lower numbers come first; ties fall back to newest year.
      order: z.number().default(100),
      // Drafts are visible with `npm run dev` but never published.
      draft: z.boolean().default(false),
    }),
});

// Technical notes: one Markdown file per note in src/content/notes/.
// src/content/notes/my-note.md -> /notes/my-note/
const notes = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/notes' }),
  schema: z.object({
    title: z.string(),
    summary: z.string(),
    date: z.coerce.date(),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

// Open-source contributions: one entry per contribution in src/content/open-source.yaml.
// Listed on the home page; no page of their own.
const openSource = defineCollection({
  loader: file('./src/content/open-source.yaml'),
  schema: z.object({
    project: z.string(),
    description: z.string(),
    status: z.string(),
    area: z.string(),
    // Month precision is enough: 2026-10. A day is allowed but not shown; YAML
    // reads a full date as a Date, so turn it back into a string.
    date: z.preprocess(
      (v) => (v instanceof Date ? v.toISOString().slice(0, 10) : v),
      z.string().regex(/^\d{4}-\d{2}(-\d{2})?$/),
    ),
    url: z.string().url(),
    linkLabel: z.string().optional(),
    writeup: z.string().startsWith('/').optional(),
  }),
});

export const collections = { work, notes, openSource };
