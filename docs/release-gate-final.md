# Final Release Gate

Date: 2026-10-02

## Verified
- Full `npm test`: PASS
- `npm run test:release-e2e`: PASS
- Real site production build inside lifecycle: PASS
- Client lifecycle: intake -> approvals -> build -> preview -> publish -> rollback: PASS
- Site output validation and smoke QA: PASS
- Dashboard security, unit tests, typecheck and production build: PASS
- Secrets audit: PASS
- Git working tree: clean

## Release boundary
The application and local/static deployment workflow are release-gated.
A real Vercel production deployment is an environment operation and requires a linked Vercel project plus deployment/runtime configuration in the target account. No repository secret values are stored in this record.

## Current checkpoint
Release code is verified on `master`; this document records the final gate evidence only.

## Update 2026-10-03 - client review loop fix

The `/v1/review/*` endpoints (change request -> revision -> rebuild -> resolve) shipped in `d439103` without coverage and were unusable over HTTP. `change_request_service._get_request` compared the SQLAlchemy `Uuid` column `ChangeRequest.client_id` against `str(client_id)` - a comparison that is always unequal - so every revision and resolve call answered `400 change request not found for client`, after the change request had been created successfully. The comparison now normalises both sides, and `ChangeRequestRepository.for_client` binds a real UUID instead of a string.

Re-verified after the fix:
- Full `npm test`: PASS (secrets audit, production-config/pilot-preflight/gate-policy, 251 Python tests, site build/output/smoke, dashboard security/unit/typecheck/build)
- `scripts/run-release-e2e.mjs`: PASS with `RELEASE_E2E_EXIT=0`
- `scripts/build-sales-demo.mjs`: PASS with `SALES_EXIT=0`
- New `apps/api/tests/test_client_review_loop.py`: 5 tests PASS (request pins the reviewed build, revision archives the reviewed artifact, rebuild + resolve records lineage, tenant isolation, decision validation)

## Deployment boundary (verified 2026-10-03)

The linked Vercel project (`ai-web-agency`) is reachable with the configured credential (read-only `GET /v2/user` returns 200) and already serves a READY production deployment. That deployment is protected by Vercel Authentication (`ssoProtection = all_except_custom_domains`), which is the expected default: it is bypassed once the client's custom domain is attached, so a public customer site requires the domain step.

The repository pins `outputDirectory` to `sites/_template-base/.next` in `vercel.json`, which is the Next.js `distDir` the Vercel framework builder validates; the template is a static export (`output: "export"`), so its `out/` directory has no `routes-manifest.json` and must not be used as the Output Directory. A full `vercel build` cannot run on this Windows host because Vercel CLI 62.2.0 fails to spawn its build shell (`spawn cmd.exe ENOENT`), so the deployment was verified against the account rather than rebuilt locally.

What is left for a real commercial pilot is operational, not code: real reviewed client content, the client domain, and a real lead. No repository secret values are recorded here.
