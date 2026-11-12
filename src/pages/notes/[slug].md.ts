import type { APIContext } from 'astro';
import { getNotes } from '../../lib/notes';

// The note as Markdown, for agents and anyone who prefers plain text.
export async function getStaticPaths() {
  const notes = await getNotes();
  return notes.map((entry) => ({ params: { slug: entry.id }, props: { entry } }));
}

type Note = Awaited<ReturnType<typeof getNotes>>[number];

export function GET({ props, site }: APIContext<{ entry: Note }>) {
  const { entry } = props;
  const d = entry.data;
  const origin = site!.origin;
  // Site-root links only work on the site itself, so make them absolute.
  const body = (entry.body ?? '').replace(/\]\(\/(?!\/)/g, `](${origin}/`).trim();
  const head = [
    `# ${d.title}`,
    '',
    d.summary,
    '',
    `- Date: ${d.date.toISOString().slice(0, 10)}`,
    ...(d.tags.length > 0 ? [`- Tags: ${d.tags.join(', ')}`] : []),
    `- URL: ${new URL(`/notes/${entry.id}/`, site)}`,
  ].join('\n');
  return new Response(`${head}\n\n${body}\n`, {
    headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
  });
}
