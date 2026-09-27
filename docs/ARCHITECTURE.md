# AI Web Agency — Architecture Decisions (v1)

Status: proposed. Inherits conventions from `C:\Users\Admin\ai-reality-studio`.

## 0. Context that shapes every decision

`ai-reality-studio` already implements the hard parts of this skeleton:

- layered app: `api/` -> `application/` (use cases) -> `services/` -> `models/` + `domain/` + `runtime/` + `providers/`
- `domain/pipeline_definition.py`: `PIPELINE_STATES`, `ALLOWED_TRANSITIONS`, `APPROVAL_CONTRACT`
- immutable versioned `Artifact` with `input_artifact_id` lineage + one-active-revision constraint
- `AgentRun`, approvals bound to a *specific artifact revision*, rejection with feedback
- provider registry with `provider_mode` = `mock | free | mixed | real`
- SQLite + SQLAlchemy 2.0, pytest, verification-first git checkpoints
- working Tavily research provider, local llama.cpp free mode, OpenAI provider

**Decision:** build AI Web Agency as a **new product on the same skeleton**, not a fork of the studio's domain
code. Reuse: base models/mixins, artifact + revision service, approval service, agent contract/runtime,
provider contract/registry *shape*, config pattern, test conventions. Replace: pipeline definition, provider
categories. Add: tenant scoping, build gate, deployment/build layer, compliance module.

## 1. Three non-negotiable principles

1. **AI generates DATA, not CODE.** The LLM never writes a React component, build config, SQL, or deploy
   command. It fills a validated content model. Code is hand-written and reviewed.
2. **Everything that reaches production is a versioned artifact.** A deploy is identified by a `build_hash`
   over (content artifact revision + content schema version + template version + design preset). Rollback =
   redeploy a previous `build_hash`. Nothing is edited in production.
3. **Seams, not systems.** Define the interface, implement exactly one provider. No plugin frameworks, no
   workflow engines, no taxonomy systems before a second implementation demands them.

## 2. ADR index

| ADR | Decision | Cost of being wrong |
|---|---|---|
| 001 | Add `org_id` to every tenant-scoped row **now**, even with one org | retrofit = every query, service and test |
| 002 | Generated sites are **separate static builds**, not part of the platform app | client uptime coupled to platform deploys |
| 003 | **Per-client build** at v1; multi-tenant runtime later behind the same content model | shared runtime = ceiling + blast radius |
| 004 | Content contract: Pydantic -> JSON Schema -> TS types + Ajv, one direction | two hand-maintained schemas drift in weeks |
| 005 | `schema_version` on artifacts is **enforced**, not decorative | unvalidated LLM output rots silently |
| 006 | Template declares `SUPPORTED_CONTENT_SCHEMA_VERSIONS` | content-model change breaks 30 live sites |
| 007 | Provider registry = registration table, not `if/elif` | adding a provider edits core code |
| 008 | LLM output must pass schema + semantic validators + build gate before publish | unvalidated content ships to a paying client |
| 009 | Publish + domain changes require approval bound to an artifact revision | unsigned publish ends trust |
| 010 | Per-org `required_approvals`; autonomy = shrinking that list | autonomy becomes a rewrite instead of config |
| 011 | `LLMInvocation` with tokens + cost per org/client | cannot price, cap or debug |
| 012 | No Docker, no Postgres, no queue required for v1 | ops overhead kills a 2-week plan |
| 013 | Deterministic SEO/AEO generators; no "SEO agent" | hallucinated structured data = deindexing risk |
| 014 | Compliance module + hard build gate (DE/DSGVO) | illegal Impressum/fonts/claims = real legal exposure |
| 015 | Customer-facing agent: EU-hostable model, approved-content retrieval only, no write actions | medical/price hallucinations are liability |
| 016 | 3-tier escape hatch (tokens -> reviewed section component -> deliberate bespoke project) | per-client template forks; demo code hand-edited |
