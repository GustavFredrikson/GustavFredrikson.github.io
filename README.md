# gustavfredrikson.github.io

Personal site at [gustavfredrikson.se](https://gustavfredrikson.se), built with [Astro](https://astro.build) and deployed to GitHub Pages by `.github/workflows/deploy.yml` on every push to `main`. The custom domain is set in the repo's Pages settings; DNS is managed at Inleed (apex A/AAAA records to GitHub Pages, `www` CNAME to `gustavfredrikson.github.io`).

```sh
npm install
npm run dev     # local dev server
npm run build   # static output in dist/
```

Site text (intro, about, email, links): `src/site.ts`.

Portfolio entries: add a Markdown file to `src/content/work/` (see `example-project.md`, a draft that only shows in `npm run dev`). Each file gets its own page at `/work/<file-name>/`. Images go in `src/assets/work/`.

Notes: add a Markdown file to `src/content/notes/` with `title`, `summary` and `date` front matter. Each gets a page at `/notes/<file-name>/` and is listed at `/notes/`.
