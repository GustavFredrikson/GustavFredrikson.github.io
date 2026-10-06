import { getCollection } from 'astro:content';

export async function getNotes() {
  const all = await getCollection('notes', (n) => import.meta.env.DEV || !n.data.draft);
  return all.sort((a, b) => b.data.date.getTime() - a.data.date.getTime());
}

export const formatDate = (d: Date) =>
  d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
