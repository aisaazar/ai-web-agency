# Production Runbook

## Required configuration
Set these values only in the deployment secret store:
- AGENCY_ENV=production
- AGENCY_ALLOWED_ORIGINS=https://<client-domain>
- AGENCY_COOKIE_SECURE=true
- AGENCY_TURNSTILE_SECRET=<server secret>
- AGENCY_DATABASE_URL=<production database URL>
- AGENCY_RESEARCH_PROVIDER=tavily
- AGENCY_LLM_PROVIDER=local
- AGENCY_LOCAL_LLM_BASE_URL=http://<llm-host>:11434/v1
- AGENCY_LOCAL_LLM_MODEL=agency-qwen3-4k
- AGENCY_NOTIFY_PROVIDER=smtp
- AGENCY_SMTP_HOST=<smtp host>
- AGENCY_SMTP_PORT=587
- AGENCY_SMTP_USERNAME=<optional smtp username>
- AGENCY_SMTP_PASSWORD=<optional smtp password>
- AGENCY_SMTP_FROM=<sender email>
- AGENCY_LEAD_NOTIFICATION_TO=<lead notification recipient>
- AGENCY_DEPLOY_PROVIDER=vercel
- VERCEL_PROJECT_ID=<project id>
- VERCEL_TOKEN=<server token>
- NEXT_PUBLIC_TURNSTILE_SITE_KEY=<public site key>
- NEXT_PUBLIC_AGENCY_LEAD_API_URL=https://<api-origin>
- NEXT_PUBLIC_AGENCY_AGENT_API_URL=https://<api-origin> when the customer agent is enabled
- NEXT_PUBLIC_AGENCY_CLIENT_ID=<client id> when `NEXT_PUBLIC_AGENCY_AGENT_API_URL` is configured
- NEXT_PUBLIC_AGENCY_SITE_ID=<site id>

Never commit secrets or copy secret values into content artifacts.

## Pre-deploy gates
Run npm test.
For a real-client pilot, run `npm run pilot:preflight` with `CONTENT_FILE` set to the reviewed client JSON. It rejects fixture content and mock provider posture before any production deployment step.
For a production site artifact, run: npm run validate:production; npm run build:site; npm run validate:output; npm run qa:smoke.
Run npm run audit:secrets before touching a deployment secret store: it fails on credential-shaped material in tracked files, on a real `.env` being tracked, and on secret-looking NEXT_PUBLIC_* names (that namespace ships to browsers).
A production content artifact must not remain a fixture and must have reviewed legal status.

## Database migrations
Schema history is tracked with Alembic under `apps/api/alembic`.
Before a production rollout, apply migrations with: `npm run db:migrate`
Check the applied revision with: `npm run db:current`
Generate a new reviewed revision only from model changes; do not hand-edit an existing applied revision.

## Database backup and restore drill
Create a backup with: npm run db:backup
Test a restore with: npm run db:restore
Keep backups outside the repository and verify a restored database opens and contains the expected tables.

## Turnstile
The site embeds the public Turnstile site key. The API validates the token server-side before accepting a lead.
Turnstile tokens expire and are single-use, so failed or expired submissions must obtain a fresh token.

## Release discipline
Do not publish until the exact build hash has passed the build gate and the human approval workflow for preview/publish is complete.
The dashboard/API deployment actions are `/v1/deploys/preview`, `/v1/deploys/publish`, `/v1/deploys/rollback`, `/v1/deploys/domain`, and `/v1/deploys/logs`.
Domain attachment requires an existing live deployment and normalizes a DNS hostname before calling the provider. Deployment logs are client-scoped and cannot be read across client boundaries.

## Production hardening
- `AGENCY_ALLOW_LEGACY_UNAUTH` is a local/test opt-in only. Production runtime preflight and API startup reject it.
- Unhandled API exceptions emit a structured, secret-safe error event with a request ID; clients receive the same request ID for support/debug correlation.
- The built-in reporter writes through the normal application logger and has no paid-service dependency. An external provider can be added later behind the same seam.
- Per-site deploy tokens are a runbook rule, not a code rule: `VERCEL_TOKEN` is the platform token and must be scoped to the target project by hand. Rotate it whenever a client leaves.
- `change_requests`, `provider_credentials`, `automation_events` and `knowledge_chunks` (docs/DOMAIN-OPS.md) are documented tables that the MVP does not yet create; maintenance work currently lives in `audit_log` and `deployments`.

## Production provider posture
Production must use real provider implementations: `AGENCY_RESEARCH_PROVIDER=tavily`, `AGENCY_LLM_PROVIDER=local`, `AGENCY_NOTIFY_PROVIDER=smtp`, and `AGENCY_DEPLOY_PROVIDER=vercel`. Mock/console/local-static providers are test or development choices and are rejected by the production preflight and API startup. The local LLM must use the bounded-context Agency model (for this PC: `agency-qwen3-4k`) rather than the upstream `qwen3:0.6b` default.
Request-level provider overrides are also rejected in production: research, LLM content generation, and preview deployment must use the configured production provider even when a caller supplies a `provider` field explicitly.

## Runtime preflight
Before starting the production API, run: npm run validate:production:runtime.
This checks production mode, HTTPS CORS origins, secure cookies, Turnstile configuration, and the selected deployment provider.
For Vercel, it requires the project ID and platform token to exist in the deployment secret store; it never prints their values.
Run this separately from the content gate: npm run validate:production.
