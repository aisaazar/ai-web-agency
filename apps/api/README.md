# apps/api

The platform app (`agency` package, `src/` layout). See `docs/CONTRACTS-AND-CONVENTIONS.md` §5 for
the intended module layout.

## What exists after Task 0.1

- `src/agency/domain/content_model.py` — the **content contract v1**: the Pydantic source of truth
  for everything a generated site renders (ADR-004, ADR-005).

## What does not exist yet

`api/`, `application/`, `services/`, `runtime/`, `providers/`, `models/`, SQLAlchemy, Alembic,
FastAPI, pytest suite. They arrive with their own tasks (`docs/PLAN-14-DAYS.md`).

## Local setup (repository-owned venv)

```powershell
py -3.12 -m venv .venv                       # from the repository root
.venv\Scripts\python.exe -m pip install -e apps/api
npm run contracts                            # regenerate JSON Schema + TS types
```

The repository never uses a globally installed interpreter: a `python` on `PATH` may belong to an
unrelated project. `scripts/py.mjs` resolves `.venv` explicitly for every npm script.
