# AI Web Agency — Template Base

This workspace is the single production Next.js static-site template used to render approved client content.

## Build

From the repository root:

```text
npm run validate
npm run typecheck:site
npm run build:site
npm run validate:output
npm run qa:smoke
node scripts/lighthouse-check.mjs
```

The content artifact is selected at build time with `CONTENT_FILE`. The default is the reference dental fixture declared by `template.config.json`. Production builds must select non-fixture client content.

## Development

```text
npm run dev:site
```

The template is a static export. The generated `out/` directory is the deployment bundle; do not use `next start` for production serving.

## Configuration

`template.config.json` is the canonical template manifest. `template.config.ts` provides the typed application view of that manifest and must not introduce independent configuration values.

## Quality gates

Content is checked against the generated contract, legal-page requirements, claims policy, URL policy, language policy, preset policy, fixture policy, and deterministic manifest rules. Browser smoke tests use Playwright + Axe; Lighthouse enforces the performance budget.

Never place secrets in this workspace's tracked files. `.env` files are local-only and ignored by Git.
