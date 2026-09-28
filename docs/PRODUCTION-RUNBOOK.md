# Production Runbook

## Required configuration
Set these values only in the deployment secret store:
- AGENCY_ENV=production
- AGENCY_ALLOWED_ORIGINS=https://<client-domain>
- AGENCY_COOKIE_SECURE=true
- AGENCY_TURNSTILE_SECRET=<server secret>
- NEXT_PUBLIC_TURNSTILE_SITE_KEY=<public site key>
- NEXT_PUBLIC_AGENCY_LEAD_API_URL=https://<api-origin>
- NEXT_PUBLIC_AGENCY_AGENT_API_URL=https://<api-origin> when the customer agent is enabled
- NEXT_PUBLIC_AGENCY_CLIENT_ID=<client id> when `NEXT_PUBLIC_AGENCY_AGENT_API_URL` is configured
- NEXT_PUBLIC_AGENCY_SITE_ID=<site id>

Never commit secrets or copy secret values into content artifacts.

## Pre-deploy gates
Run npm test.
For a production site artifact, run: npm run validate:production; npm run build:site; npm run validate:output; npm run qa:smoke.
Run npm run audit:secrets before touching a deployment secret store: it fails on credential-shaped material in tracked files, on a real `.env` being tracked, and on secret-looking NEXT_PUBLIC_* names (that namespace ships to browsers).
A production content artifact must not remain a fixture and must have reviewed legal status.

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

## Deferrals (recorded, not forgotten)
- Error reporting (Sentry or equivalent) is not wired: the API logs to stdout only. Add the SDK behind a provider seam before the first paying client, not before.
- Per-site deploy tokens are a runbook rule, not a code rule: `VERCEL_TOKEN` is the platform token and must be scoped to the target project by hand. Rotate it whenever a client leaves.
- `change_requests`, `provider_credentials`, `automation_events` and `knowledge_chunks` (docs/DOMAIN-OPS.md) are documented tables that the MVP does not yet create; maintenance work currently lives in `audit_log` and `deployments`.
