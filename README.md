# gustavfredrikson.github.io

Personal site, built with [Astro](https://astro.build) and deployed to GitHub Pages by `.github/workflows/deploy.yml` on every push to `main`.

```sh
npm install
npm run dev     # local dev server
npm run build   # static output in dist/
```

Site text (intro, about, email, links): `src/site.ts`.

Portfolio entries: add a Markdown file to `src/content/work/` (see `example-project.md`, a draft that only shows in `npm run dev`). Each file gets its own page at `/work/<file-name>/`. Images go in `src/assets/work/`.
