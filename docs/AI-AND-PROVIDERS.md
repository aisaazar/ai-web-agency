# AI vs Deterministic, Provider Matrix, Postponed

## 1. AI versus deterministic code

| Task | AI | Deterministic code |
|---|---|---|
| Web research synthesis | yes (unstructured -> structured, with provenance) | — |
| Copywriting, tone, DE `Sie` translation | yes | length/readability/banned-claim validators |
| Section selection & ordering | proposes | allowlist validation + rules table decides |
| Design tokens, colour, contrast, fonts | — | preset + WCAG contrast math |
| JSON-LD, sitemap, robots, llms.txt, hreflang, canonicals | — | generated from approved facts |
| Build, validate, deploy, DNS, rollback | — | pipeline only |
| Lead routing, status transitions, notifications | — | pipeline only |
| Customer chat | yes (RAG over approved content) | scope guard, refusal, PII redaction, escalation |
| Fact extraction from client's site / search | yes | reconciliation + provenance + human approval |

**Genuinely useful AI:** turning messy external input (client's existing site, search results, an intake form)
into typed data, and turning typed data into prose.
**Never AI:** anything with a correct answer, anything that writes to production, anything security-relevant.

## 2. Provider-agnostic matrix

| Capability | v1 implementation | Interface to freeze | Later |
|---|---|---|---|
| `llm` | `mock`, `local` (llama.cpp/Ollama), `openai` | `complete(LLMRequest) -> LLMResponse` (typed) | Anthropic, Mistral EU, Azure EU |
| `research` | `mock`, `tavily` (exists) | `search()`, `fetch()` (SSRF-guarded) | Brave, Serper, internal crawler |
| `deploy` | `local_static` (free/tests), `vercel` | `create_preview`, `promote`, `rollback`, `attach_domain`, `logs` | Netlify, Cloudflare Pages, Hetzner |
| `notify` | `console`, `smtp`/`brevo` | `send(Notification)` | n8n webhook, Slack |
| `storage` | `local_fs` | `put`/`get`/`signed_url` | S3 / R2 |
| `analytics` | platform-side conversion events | `event()` | self-hosted Umami / Plausible |
| `secrets` | `.env` + per-org encrypted columns | `get(org, key)` | KMS / Vault |

**Rule:** keep `mock` + one free/local implementation for *every* category. That property is what makes the
entire test suite offline and deterministic. Losing it costs days of flaky CI.

## 3. Modular vs hard-coded (the honest split)

**Must be provider-agnostic now** (a wrong choice is expensive or a lock-in): LLM, research, deploy/hosting,
notify/email, storage, secrets, analytics.

**Should NOT be abstracted in v1** (premature abstraction, one implementation ever):
template engine, chart/OG rendering, form spam protection, scheduling/booking, auth mechanics, ORM.

## 4. Deliberately postponed (do not build in v1)

Billing/Stripe · self-serve signup · visual page builder · multiple templates · 3D/immersive ·
autonomous prospecting & scraping · multi-agency (reseller) tenancy · Postgres row-level security ·
Temporal/Prefect/Celery · vector database · invoice automation · client-editable CMS · A/B testing ·
fine-tuning · languages beyond DE/EN · mobile apps · per-client repos · automated DNS purchase.

Each is postponed, not rejected — every one is reachable through a seam named above.
