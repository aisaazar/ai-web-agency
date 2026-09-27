# Domain Model — Interaction, Operations, Portability

## Demand & interaction

| Entity | Purpose | Key fields |
|---|---|---|
| `lead_submissions` | form/agent leads | `site_id`, `client_id`, `payload_json`, `name`, `email`, `phone`, `message`, `consent_at`, `spam_score`, `status` (`new`/`contacted`/`qualified`/`won`/`lost`), `utm_json` |
| `lead_events` | status history | `lead_submission_id`, `from_status`, `to_status`, `actor`, `note` |
| `conversations` / `messages` | customer-facing agent | `site_id`, `visitor_ref` (pseudonymous), `escalated`, `transcript_hash`; `role`, `content`, `retrieved_chunk_ids`, `model` |
| `knowledge_chunks` | approved-content index | `site_version_id`, `section`, `text`, `embedding_ref`, `source_fact_keys` |
| `change_requests` | client-requested edits | `site_id`, `requested_by`, `body`, `status`, `resulting_build_hash` |

`change_requests` + `resulting_build_hash` is the maintenance workflow and the scope-creep audit trail in one
table. Every free edit a client asks for is recorded, costed and traceable — that is how maintenance stops
eating margin.

## Operations & safety

| Entity | Purpose | Key fields |
|---|---|---|
| `llm_invocations` | cost + debuggability | `org_id`, `client_id`, `agent_run_id`, `provider`, `model`, `prompt_hash`, `tokens_in`, `tokens_out`, `cost_micros`, `latency_ms`, `status` |
| `provider_credentials` | per-org secrets | `org_id`, `provider`, `ciphertext`, `key_version`, `rotated_at` |
| `audit_log` | who did what | `org_id`, `actor`, `action`, `entity_type`, `entity_id`, `before_json`, `after_json`, `ip`, `created_at` |
| `automation_events` | outbound webhook | `site_id`, `kind`, `payload_json`, `delivered_at`, `attempts` |

## Portability rules (learned from the studio schema)

The studio's `Artifact` uses `Index(..., sqlite_where=text("is_active = 1"))`. That is SQLite-only syntax and
silently blocks a move to Postgres. Rules from day one:

1. Partial indexes: supply `sqlite_where` **and** `postgresql_where`, or avoid them.
2. Alembic from the first migration with `render_as_batch=True` (SQLite can't `ALTER` most things).
3. No `datetime.utcnow()` as a column default; one UTC helper, naive-in-SQLite / aware-in-Postgres.
4. JSON in `Text` is fine **only** behind a typed accessor that validates via Pydantic.
5. No SQLite-specific SQL (`INSERT OR IGNORE`, `strftime`) in services; keep dialect specifics in a repository layer.
6. `org_id` + (where relevant) `client_id` on every tenant-scoped row, with exactly one scoped accessor
   function used by all services.

## Non-negotiable invariants (write these as tests from day 1)

- An artifact revision is never mutated; a change creates a new revision and flips `is_active`.
- An approval is bound to one artifact revision and cannot be reused for another.
- A deployment is impossible without a passing `build_validation` set for that exact `build_hash`.
- Content copy may only derive from `client_facts` where `status = approved`.
- No query returns rows belonging to another `org_id` (cross-tenant test suite proves it).
- No published page exists without the jurisdiction-required legal pages.
- Every `LLMInvocation` is attributed to an `org_id` and a `client_id`.

These seven invariants are the difference between a demo and something you can charge money for.
