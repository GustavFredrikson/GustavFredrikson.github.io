# gustavfredrikson.github.io

Personal site at [gustavfredrikson.se](https://gustavfredrikson.se), built with [Astro](https://astro.build) and deployed to GitHub Pages by `.github/workflows/deploy.yml` on every push to `main`. The custom domain is set in the repo's Pages settings; DNS is managed at Inleed (apex A/AAAA records to GitHub Pages, `www` CNAME to `gustavfredrikson.github.io`).

```sh
npm install
npm run dev     # local dev server
npm run build   # static output in dist/
```

Site text (intro, about, email, links): `src/site.ts`.

Portfolio entries: add a Markdown file to `src/content/work/` (see `example-project.md`, a draft that only shows in `npm run dev`). Each file gets its own page at `/work/<file-name>/`. Images go in `src/assets/work/`. Cover images are rendered from `tools/covers/<name>.html` with `tools/covers/render.sh <name>`. A cover morphs between its home tile and its project page through a view transition, in browsers that support it.

Notes: add a Markdown file to `src/content/notes/` with `title`, `summary` and `date` front matter. Each gets a page at `/notes/<file-name>/`, is listed at `/notes/` and goes into the RSS feed at `/rss.xml` (`src/pages/rss.xml.ts`). A note with three or more `##` headings gets an "On this page" outline on wide screens.

For agents: each note is also served as Markdown at `/notes/<file-name>.md` (`src/pages/notes/[slug].md.ts`), and `/llms.txt` lists the notes and work pages (`src/pages/llms.txt.ts`).

Raw HTML inside a work page or note, like the reply toggle on the thesis page, must have no blank lines: a blank line ends a Markdown HTML block.

Print: the `@media print` block at the end of `src/styles/global.css` forces the light theme and hides navigation.

Open source: add an entry to `src/content/open-source.yaml` (fields are described at the top of the file). Entries are listed on the home page, newest first.
