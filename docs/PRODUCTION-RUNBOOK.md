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
- NEXT_PUBLIC_AGENCY_SITE_ID=<site id>

Never commit secrets or copy secret values into content artifacts.

## Pre-deploy gates
Run npm test.
For a production site artifact, run: npm run validate:production; npm run build:site; npm run validate:output; npm run qa:smoke.
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