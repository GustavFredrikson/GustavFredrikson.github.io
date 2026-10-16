import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://gustavfredrikson.se',
  integrations: [sitemap()],
  // No default colour: global.css picks --shiki-light or --shiki-dark so code
  // follows the theme toggle, and keeps its own background.
  markdown: {
    shikiConfig: {
      themes: { light: 'github-light-high-contrast', dark: 'github-dark-default' },
      defaultColor: false,
    },
  },
});
