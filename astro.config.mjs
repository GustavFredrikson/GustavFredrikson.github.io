import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://gustavfredrikson.se',
  integrations: [sitemap()],
  // Code blocks take their colours from global.css so they follow light/dark mode.
  markdown: { syntaxHighlight: false },
});
