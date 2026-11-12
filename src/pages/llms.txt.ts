import type { APIContext } from 'astro';
import { getNotes } from '../lib/notes';
import { getWork } from '../lib/work';
import { site as siteText } from '../site';

// A map of the site for language models, in the llmstxt.org shape.
export async function GET({ site }: APIContext) {
  const [notes, work] = await Promise.all([getNotes(), getWork()]);
  const url = (path: string) => new URL(path, site).href;
  const lines = [
    `# ${siteText.name}`,
    '',
    `> ${siteText.intro}`,
    '',
    '## Notes',
    '',
    ...notes.map((n) => `- [${n.data.title}](${url(`/notes/${n.id}.md`)}): ${n.data.summary}`),
    '',
    '## Work',
    '',
    ...work.map((w) => `- [${w.data.title}](${url(`/work/${w.id}/`)}): ${w.data.summary}`),
  ];
  return new Response(`${lines.join('\n')}\n`, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
