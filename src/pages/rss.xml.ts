import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { getNotes } from '../lib/notes';
import { site } from '../site';

export async function GET(context: APIContext) {
  const notes = await getNotes();
  return rss({
    title: `${site.name} — Notes`,
    description: "Technical notes on systems I've built and the decisions behind them.",
    site: context.site!,
    items: notes.map((n) => ({
      title: n.data.title,
      description: n.data.summary,
      pubDate: n.data.date,
      link: `/notes/${n.id}/`,
      categories: n.data.tags,
    })),
  });
}
