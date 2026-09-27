# packages/contracts

**Generated. Never hand-edited** (`docs/CONTRACTS-AND-CONVENTIONS.md` §5, ADR-004).

| File | Produced by |
|---|---|
| `content.schema.json` | `scripts/export_contracts.py` (Pydantic `model_json_schema()`) |
| `src/content.ts` | `scripts/emit-contract-types.mjs` (JSON Schema -> TypeScript) |

Source of truth: `apps/api/src/agency/domain/content_model.py`.

```powershell
npm run contracts         # regenerate both artifacts
npm run contracts:export  # schema only
npm run contracts:types   # TypeScript only
npm run contracts:check   # fail if content.schema.json is stale
```

Consumers resolve `@ai-web-agency/contracts` (types) and `@ai-web-agency/contracts/content.schema.json`
(the runtime validator input of `sites/_template-base`). The package intentionally exposes **no runtime
entry point**: content types are erased at compile time, the schema is data.
