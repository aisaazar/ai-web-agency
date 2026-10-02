# AI Web Agency

AI generates content **data**; hand-written code renders it into static, gated client sites.
The [`docs/`](docs) directory is the source of truth (8 documents). Nothing in this repository
re-decides an architecture question those documents already answered; when code and docs disagree,
the docs win and the code is a bug.

| Document | Read it for |
| --- | --- |
| [DELIVERY-PLAN.md](docs/DELIVERY-PLAN.md) | active delivery deadline, acceptance line, and remaining pilot work |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | the ADR table (ADR-001 …) |
| [DOMAIN-MODEL.md](docs/DOMAIN-MODEL.md) | tables, pipeline states, `build_hash` |
| [CONTRACTS-AND-CONVENTIONS.md](docs/CONTRACTS-AND-CONVENTIONS.md) | repo layout, naming, versioning |
| [PIPELINE-AND-GATE.md](docs/PIPELINE-AND-GATE.md) | what the gate must prove before a publish |
| [DOMAIN-OPS.md](docs/DOMAIN-OPS.md) | deploy, rollback, handover |
| [SECURITY-AND-RISKS.md](docs/SECURITY-AND-RISKS.md) | claim/legal/DSGVO risk model |
| [AI-AND-PROVIDERS.md](docs/AI-AND-PROVIDERS.md) | provider registry, deterministic-vs-LLM split |

## Layout

```
apps/api/src/agency/      Python control plane (domain, pipeline, gate, build service)
packages/contracts/       the generated hand-off artefacts (see below)
sites/_presets/           hand-authored design token presets
sites/_template-base/     THE one production template (Next.js 15, TypeScript, Tailwind v4, SSG)
```

`sites/_template-base` has no database, API or secret dependency: it reads one validated content
artifact selected at build time, so one template builds every client.

## Generated contracts

`packages/contracts/content.schema.json` and `packages/contracts/src/content.ts` are **generated,
never hand-edited** (ADR-004: Pydantic → JSON Schema → TypeScript). They are committed on purpose so
that a clone can run every gate without a Python toolchain.

```
npm run contracts          # regenerate both artefacts
npm run contracts:check    # fail if the committed artefacts drifted from the model
```

## Commands

```
npm install                # workspace root (Node >= 20.9); .venv/ for Python is created on demand
npm test                   # python tests + the whole site chain
npm run test:python        # pytest apps/api/tests
npm run validate           # content gate: schema, claims, urls, language, legal pages (dev mode)
npm run validate:production# the same gate with fixture content made fatal (what CI runs per client)
npm run audit:secrets      # tracked files: credential shapes, real .env, secret-looking NEXT_PUBLIC_* names
npm run build:site         # tokens -> content gate -> next build -> sites/_template-base/out
npm run validate:output    # prove the exported artefacts and self-hosted fonts exist
npm run qa:smoke           # serve out/, crawl every route, axe scan for serious/critical issues
npm run sales:demo:wittmann # build + validate a private prospect redesign under .artifacts/
```

`PRODUCTION_BUILD=1` plus `CONTENT_FILE=<basename>` is how a real client is built; the reference
fixture (`sites/_template-base/content.dental-clinic.json`) is marked `meta.is_fixture = true` and can
never reach a production build.

## Constraints

No `.env` file is read, printed or committed (`.env.example` is the only tracked one). Nothing here
deploys or touches DNS. `C:\Users\Admin\ai-reality-studio` is unrelated and out of scope.
