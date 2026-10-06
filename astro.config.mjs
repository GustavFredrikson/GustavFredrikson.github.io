import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://gustavfredrikson.se',
  // Code blocks take their colours from global.css so they follow light/dark mode.
  markdown: { syntaxHighlight: false },
});
