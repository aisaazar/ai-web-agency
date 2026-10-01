# Commercial Pilot Checklist

Target: first real client -> real website -> real domain -> live -> one real lead.

## 1. Accounts / credentials

### Tavily
Create a Tavily account and API key. The current free Researcher plan provides 1,000 API credits/month and does not require a credit card.

Set privately:
- TAVILY_API_KEY

Never commit or paste the secret into tracked files.

### Vercel
Create or use a Vercel account and create a project for the customer site.

Collect privately:
- VERCEL_PROJECT_ID
- VERCEL_TOKEN

The repository production posture expects the deployment provider to be Vercel and the token to be scoped to the target project.

### SMTP
Use an SMTP account for lead notifications. For a small pilot, a Google account can be used with an app password when 2-Step Verification is enabled.

Set privately:
- AGENCY_SMTP_HOST
- AGENCY_SMTP_PORT
- AGENCY_SMTP_USERNAME
- AGENCY_SMTP_PASSWORD
- AGENCY_SMTP_FROM
- AGENCY_LEAD_NOTIFICATION_TO

## 2. Client onboarding

For one real client collect:
- legal business name
- brand name
- address
- phone/email
- opening hours
- services
- approved claims/facts
- domain
- legal/privacy text
- written approval for production use

The prepared content must have:
- meta.is_fixture = false
- compliance.legal_review_status = reviewed
- business.jurisdiction = DE
- supported content_schema_version

Use the repository pilot content preparation command with the reviewed JSON and client slug.

## 3. Production configuration

Set privately in the production secret store:
- AGENCY_ENV=production
- AGENCY_ALLOWED_ORIGINS=https://<client-domain>
- AGENCY_COOKIE_SECURE=true
- AGENCY_TURNSTILE_SECRET
- AGENCY_DATABASE_URL
- AGENCY_RESEARCH_PROVIDER=tavily
- AGENCY_LLM_PROVIDER=local
- AGENCY_LOCAL_LLM_BASE_URL
- AGENCY_LOCAL_LLM_MODEL=agency-qwen3-8k
- AGENCY_NOTIFY_PROVIDER=smtp
- AGENCY_DEPLOY_PROVIDER=vercel
- Vercel/Tavily/SMTP values above
- production public URL/site identifiers and Turnstile site key

Run the production runtime validator and pilot preflight before deployment.

## 4. Release

Required sequence:
1. Build reviewed client content.
2. Run content and production gates.
3. Create preview with the exact build hash.
4. Human approve preview.
5. Publish.
6. Attach the client domain.
7. Verify the live site from an external browser.
8. Submit one real lead.
9. Verify the lead in dashboard and notification/email.
10. Verify rollback path.
11. Final Git status clean and push.

Do not call the pilot complete until every release check is verified.
