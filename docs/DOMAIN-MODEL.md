# AI Web Agency — Domain Model (v1)

Reused unchanged from `ai-reality-studio`: `Project` (here: an *engagement*), `Artifact` + revision service,
`AgentRun`, `Approval`, `PipelineState` / `PipelineTransition` / `PipelineError`, model mixins, database layer.

## Two concepts people wrongly merge

- **Org** = the agency using this platform (v1: exactly one row, but `org_id` on every table).
- **Client** = the end business whose website we build (a domain entity, **not** a tenant).

Conflating them forces a rewrite the moment you sell the platform to a second agency. v1 tenancy means
*multi-client*, with the schema already org-scoped.

## Tenancy

| Entity | Purpose | Key fields |
|---|---|---|
| `orgs` | agency tenant | `name`, `slug`, `required_approvals` (json list), `default_jurisdiction`, `llm_budget_micros` |
| `users` | platform users | `email`, `password_hash`, `is_active`, `totp_secret_ref` |
| `memberships` | user<->org role | `org_id`, `user_id`, `role` (`owner`/`operator`/`reviewer`) |

## Client understanding

| Entity | Purpose | Key fields |
|---|---|---|
| `clients` | the business | `org_id`, `name`, `slug`, `category`, `jurisdiction`, `locale`, `existing_url`, `gbp_url`, `status` |
| `client_facts` | **typed, approved business truth** | `client_id`, `key`, `value`, `value_type`, `source_kind` (`intake`/`client_site`/`search`/`human`), `source_ref`, `confidence`, `status` (`proposed`/`approved`/`rejected`), `approved_by` |
| `client_contacts` | people & channels | `client_id`, `role`, `name`, `email`, `phone` |
| `research_runs` | one research execution | `client_id`, `agent_run_id`, `provider`, `query_plan_json` |
| `research_sources` | evidence | `research_run_id`, `url`, `title`, `fetched_at`, `content_hash`, `excerpt` |

`client_facts` with provenance + approval is the most valuable table in the system: copy may only be generated
from **approved** facts. That is what prevents invented phone numbers, invented prices and invented
qualifications appearing on a client's live site.

## Deliverable

| Entity | Purpose | Key fields |
|---|---|---|
| `sites` | a client's website | `org_id`, `client_id`, `template_id`, `design_preset_id`, `current_build_hash`, `live_url`, `status` |
| `site_versions` | **the deployable unit** (immutable) | `site_id`, `build_hash`, `content_artifact_id`, `content_schema_version`, `seo_manifest_artifact_id`, `template_version`, `design_preset_id` |
| `deploys` | one deployment attempt | `site_version_id`, `provider`, `provider_deploy_id`, `environment` (`preview`/`production`), `status`, `url`, `log_ref`, `started_at`, `finished_at` |
| `domains` | DNS/TLS state | `site_id`, `fqdn`, `provider`, `dns_status`, `tls_status`, `verified_at` |
| `build_validations` | evidence for the gate | `site_version_id`, `check_name`, `passed`, `detail_json` |

`build_hash = sha256(content_artifact_id + content_schema_version + template_version + design_preset_id +
lockfile_hash)`. Same hash => byte-identical output. That makes caching, rollback and "is this version live"
trivial. Store it; never reconstruct a deploy from a mutable pointer.

Registered artifact types: `business_facts`, `research_report`, `brand_kit`, `design_plan`, `content_model`,
`seo_manifest`, `build_manifest`.
