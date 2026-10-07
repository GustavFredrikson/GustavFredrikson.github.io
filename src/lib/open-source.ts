import { getCollection } from 'astro:content';

export async function getContributions() {
  const all = await getCollection('openSource');
  // YYYY-MM(-DD) strings sort chronologically as text.
  return all.sort((a, b) => b.data.date.localeCompare(a.data.date));
}

export const formatMonth = (date: string) =>
  new Date(`${date.slice(0, 7)}-01T00:00:00Z`).toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' });

// Link text for the upstream source, e.g. "TecharoHQ/anubis pull request #2004".
export function sourceLabel(url: string) {
  const u = new URL(url);
  const [owner, repo, kind, ref, tag] = u.pathname.split('/').filter(Boolean);
  if (u.hostname !== 'github.com' || !owner || !repo) return u.hostname + u.pathname.replace(/\/$/, '');
  const name = `${owner}/${repo}`;
  if (kind === 'pull' && ref) return `${name} pull request #${ref}`;
  if (kind === 'issues' && ref) return `${name} issue #${ref}`;
  if (kind === 'commit' && ref) return `${name} commit ${ref.slice(0, 7)}`;
  if (kind === 'releases' && ref === 'tag' && tag) return `${name} release ${tag}`;
  return name;
}
