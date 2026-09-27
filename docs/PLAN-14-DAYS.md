# MVP Scope and 14-Day Plan

## Assumptions (if any is false, the plan is false)

One senior dev + AI assistance, reusing the `ai-reality-studio` skeleton. No Docker, no Postgres, no queue,
no Kubernetes. One industry template (dental/health) + one presets set. Manual DNS. Manual invoicing.
Reference client: a real dental clinic in Germany.

## MVP in scope

Intake -> typed business facts with provenance -> facts approval -> research (Tavily) -> content generation
with validators -> design preset selection -> SEO/AEO manifest -> static build -> build gate -> Vercel
preview -> preview approval -> publish to real domain -> lead capture -> notifications -> dashboard
(clients, artifacts, approvals, deploys, rollback) -> per-org auth + roles -> LLM cost log -> audit log ->
customer-facing chat agent over approved content with escalation to human contact.

## MVP out of scope

Everything in `AI-AND-PROVIDERS.md` section 4. Concretely: no second template, no 3D, no page builder, no
billing, no self-serve signup, no automated DNS purchase, no reseller tenancy, no vector DB (SQLite FTS5 or a
tiny embedded index is enough), no autonomous lead discovery, no client CMS.

## Day-by-day

| Day | Goal | Definition of done |
|---|---|---|
| 0 | Decisions + accounts | ADRs committed; Vercel/Cloudflare/Brevo/Tavily/LLM keys in `.env`; repo scaffolded from the studio skeleton; Alembic initialised |
| 1 | Domain, DB, tenant scoping | migration creates all v1 tables with `org_id`; pipeline definition + transition service + tests; fixture dental clinic seeded |
| 2 | **Hand-built reference site** | `sites/_template-base` renders the dental clinic from `content.dental-clinic.json`; live Vercel preview; Impressum, Datenschutz, sitemap, robots, llms.txt, LocalBusiness JSON-LD; Lighthouse >= 95; self-hosted fonts |
| 3 | Content contract | `ContentModel` -> JSON Schema -> TS types + Ajv; template declares `SUPPORTED_CONTENT_SCHEMA_VERSIONS`; contract test fails on unknown version |
| 4 | Intake + facts + gate | intake API -> `FACTS_EXTRACTED`; facts with provenance/confidence; approval gate; rejected fact provably cannot reach content |
| 5 | Research | Tavily wired to `research` category; sources stored with hashes; research report artifact; reconciliation against known facts; gate |
| 6 | Content generation | per-section copy (DE, `Sie`), schema-validated, repair loop, banned-claims validator, length/readability checks, facts-only test |
| 7 | Design system | 3 token presets (health/corporate/warm); WCAG contrast validator; deterministic preset-selection rule table; fonts self-hosted |
| 8 | SEO/AEO manifest | generators for meta, canonical, hreflang, sitemap, robots (AI crawlers allowed), llms.txt, JSON-LD from approved facts; OG images at build |
| 9 | Build + gate + deploy | gate runs all checks and writes `build_validations`; create an immutable preview from the exact `build_hash`; human preview approval; `promote` + `attach_domain`; rollback by `build_hash` |
| 10 | Auth + dashboard | per-org login, roles, single scoped accessor; dashboard: clients, pipeline state, artifact diff, approvals, deploy history, rollback; cross-tenant test suite |
| 11 | Lead capture + notifications | form -> `lead_submissions` -> notify (email/webhook to n8n) -> dashboard list -> CSV export; honeypot + time-trap + Turnstile; consent capture; conversion events |
| 12 | Customer agent | RAG over approved content only; scope guard, refusal rules, PII redaction, escalation; transcript logging; consent notice; degrades to static FAQ if provider is down |
| 13 | Hardening | SSRF allowlist + prompt-injection tests; secrets audit; rate limits; audit log; backup + restore drill; per-client LLM cost report; Sentry; runbooks |
| 14 | Real client dress rehearsal | real dental clinic taken end to end to a live domain; client approval recorded; docs updated with deferrals; git checkpoint |

## Buffer reality

Days 6, 9 and 12 always overrun. Cut in this order:
1. customer agent -> static FAQ + contact widget
2. OG image generation
3. research reconciliation depth
4. second language

Never cut: the build gate, the facts-provenance rule, or the legal pages. Those three are the product.

## Pilot success metric

The 2-week MVP has exactly one success criterion: **one real client site live on their own domain, with a
real lead captured through it.** Not "the pipeline works". A captured lead is the only proof that the
artifact is commercially real.
