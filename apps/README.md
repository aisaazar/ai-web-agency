# apps/

Platform applications. Repository layout follows `docs/CONTRACTS-AND-CONVENTIONS.md` §5.

| Path | Status | Purpose |
|---|---|---|
| `apps/README.md` | this file | placeholder so the folder exists in git |
| `apps/api/` | started (content contract only) | platform API, use cases, services, domain, runtime, providers, models |
| `apps/dashboard/` | not started | internal Next.js dashboard (clients, approvals, deploys) — Day 10 |

Not yet present on purpose (see `docs/PLAN-14-DAYS.md`): database layer, Alembic, FastAPI routes,
provider registry, agent runtime. They land in their own tasks; this scaffold does not pre-build them.
