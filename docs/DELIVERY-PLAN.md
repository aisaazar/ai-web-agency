# Delivery Plan ? Sunday, October 4, 2026

## Delivery target

The AI Web Agency is being prepared for handover by **Sunday, October 4, 2026**.
The `PLAN-14-DAYS.md` file is retained as historical build-order documentation; it is not the active deadline.

## Current release state

The engineering MVP is at release-candidate stage:

- API/domain workflow implemented and covered by the full Python suite.
- Alembic migration history is committed and migration tests pass.
- Dashboard reads scoped data from the agency API rather than mock overview data.
- Health, Corporate, and Warm design presets pass deterministic contrast/token checks.
- Static site build, output validation, accessibility smoke checks, and dashboard production build pass.
- Preview, publish, domain attachment, deployment logs, lead capture, dashboard reporting, and rollback are covered by HTTP release E2E.
- Customer-facing agent has consent, approved-content scoping, PII redaction, escalation, transcript logging, and rate limits.
- Production configuration fails closed when required security/runtime configuration is absent.

## Remaining delivery work

The remaining work is operational rather than architectural: run one real-client dress rehearsal using real reviewed client content, the real domain, the production deployment secret store, and a real lead submission.

The reference dental fixture must remain a fixture and must never be used as proof of commercial launch readiness.

## Sunday commercial acceptance line

A handover is considered complete when all of the following are true:

1. A real client site is built from the shared template using approved client data.
2. Production content passes the production content gate and legal review status is recorded.
3. The exact build hash is previewed, human-approved, published, and reversible by rollback.
4. The client domain is attached and serving the expected static site.
5. A real lead is captured successfully and appears in the dashboard/export path.
6. The final Git checkpoint is clean and pushed to `origin/master`.
7. Production runbook values and deployment steps are handed over without exposing secrets.

## Explicitly deferred

The following remain outside Sunday delivery scope: second templates, 3D sites, page-builder functionality, billing, self-serve signup, automated DNS purchase, reseller tenancy, vector infrastructure beyond embedded/local search, autonomous lead discovery, and client CMS functionality.

## Engineering checkpoint ? October 1, 2026

The full repository test command passes after production-provider hardening. Production startup and request paths now reject mock research, mock LLM content generation, console notifications, and local-static deployment posture. Dashboard workflow defaults follow configured providers instead of silently selecting a mock LLM provider. The free local LLM path is packaged as `agency-qwen3-8k` with an 8192-token context to avoid the upstream 40K-context failure observed on the Windows pilot host.

Verified in this checkpoint: full Python test suite, production configuration tests, content gates, all design-token presets, static site build/output/smoke QA, dashboard security/typecheck/build, release E2E, and local browser checks for the public site and dashboard login.

This does not replace the real-client acceptance line: a real client, real domain, real production provider credentials, and a real lead are still required before commercial handover is declared complete.
