# Security, Compliance and Risk Register

## Security & compliance checklist (all blocking for v1)

- [x] LLM output is plain-text content only; no HTML/markdown rendering surface and no `dangerouslySetInnerHTML`
- [x] Fetched/scraped content is untrusted input data only: it is validated/bounded, never drives tool calls, deploy actions, file paths or SQL
- [x] Prompt-injection regression tests: untrusted research text cannot widen the fact set, replace the operator instruction or bypass the claims validator, and copy hidden inside approved content cannot turn the customer agent into an advice-giver (`apps/api/tests/test_prompt_injection.py`)
- [x] Fetch provider: scheme allowlist, block private/loopback/link-local IPs, cap redirects + body size, timeout
- [ ] One scoped repository layer; cross-tenant test suite; every query carries `org_id`
- [x] Per-site deploy token scoped to one project; no org-wide token inside a client build; no secrets in build output — the static build runs with secret-like env names removed (`_build_environment`) and `npm run audit:secrets` fails on credential shapes, tracked `.env` files and secret-looking `NEXT_PUBLIC_*` names
- [x] Studio auth: argon2/bcrypt hashes, 2FA-ready, secure + httpOnly cookies, CSRF, rate limits, session rotation
- [x] LLM budget caps per org **and** per client; bounded retries; hard fail when budget is exceeded
- [x] Generated sites: strict CSP, no third-party trackers by default, **no Google Fonts CDN** (German court rulings); enforced by build output generation + validation
- [ ] DE: Impressum, Datenschutz, cookie consent, AVV with processors, EU data residency where personal data is involved
- [ ] Health/legal claims: banned-claim validator + human approval; customer agent must not give medical advice
- [x] Backups: nightly DB dump + artifact payloads; one restore drill actually performed
- [x] Pseudonymous visitor refs for chat; no PII in `llm_invocations` or logs; retention policy documented

Note plainly: this is engineering risk reduction, not legal advice. Have a German lawyer review the Impressum,
Datenschutz and the customer-agent disclaimer templates once, then reuse them per client.

## Risk register — top 10 architectural risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| 1 | LLM writes site code per client | unmaintainable, unverifiable, no rollback | data-not-code rule (ADR-001/008); template + content model |
| 2 | Missing `org_id` from day one | rewrite of every query, service, test | ADR-001; migration on day 1 |
| 3 | Client sites coupled to platform runtime | one bug takes down all clients | ADR-002; separate static builds |
| 4 | Unenforced `schema_version` / untyped `payload_json` | silent content corruption after a model change | ADR-005/006; validation at artifact boundary |
| 5 | Untyped deploy provider contract | malformed payload reaches production | typed `DeploymentProvider` + build gate |
| 6 | `if/elif` provider registry | adding providers edits core; change becomes scary | registration table (ADR-007) |
| 7 | No cost accounting | unpriced, uncapped LLM spend per client | `llm_invocations` + budget caps (ADR-011) |
| 8 | Prompt injection via scraped client content | exfiltration, malicious publish | untrusted-content rule; no tool calls from content; tests |
| 9 | SQLite-only SQL / partial indexes | painful Postgres migration at scale | portability rules; Alembic batch mode |
| 10 | Template forks per client ("just this once") | production builds diverge; no reuse; margin dies | 3-tier escape hatch (ADR-016), enforced in code review |

## Business risks the architecture cannot fix (be honest about these)

1. **Content quality and truth.** A German dental clinic's site is regulated; a wrong claim is their problem
   *and* yours. Mitigated by facts provenance + gates, not eliminated.
2. **Access to real client data.** You cannot build a good site without practice photos, team info, opening
   hours and treatment list. The intake bottleneck is human, not technical — design intake as a guided
   questionnaire the client fills, never as a discovery you do for them.
3. **SEO/AEO is a long game.** You cannot promise rankings in 2 weeks. Promise structure, speed,
   accessibility and AI-readability; promise outcomes only in a maintenance contract.
4. **The second client is harder than the first.** Client #1 will be hand-held. If the template + content
   model are not genuinely reusable, client #2 costs the same as client #1 and there is no business.
5. **Hosting and handover exit.** Decide in writing who owns the domain, the content and the repo. Static
   export means the client can always leave — that is a *selling point* for a serious agency, not a risk.
