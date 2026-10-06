import { getCollection } from 'astro:content';

export async function getWork() {
  const all = await getCollection('work', (w) => import.meta.env.DEV || !w.data.draft);
  return all.sort((a, b) => a.data.order - b.data.order || b.data.year - a.data.year);
}
