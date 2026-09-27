# Contracts, Registry, Agent Runtime, Orchestration

## 1. Provider contracts (frozen v1 interfaces)

Typed where a wrong payload is a production incident. The studio's `dict in / dict out` contract is fine for
generative steps and is **not** fine for deployment.

```python
class LLMProvider(Protocol):
    name: str
    def complete(self, req: LLMRequest) -> LLMResponse: ...

class ResearchProvider(Protocol):
    name: str
    def search(self, query: str, *, max_results: int) -> list[Source]: ...
    def fetch(self, url: str) -> FetchedPage: ...          # SSRF-guarded

class DeploymentProvider(Protocol):
    name: str
    def create_preview(self, bundle: BuildBundle) -> DeployResult: ...
    def promote(self, deploy_ref: str) -> DeployResult: ...
    def rollback(self, site_id: str, to_build_hash: str) -> DeployResult: ...
    def attach_domain(self, site_id: str, fqdn: str) -> DomainResult: ...
    def logs(self, deploy_ref: str) -> str: ...

class NotifyProvider(Protocol):
    def send(self, notification: Notification) -> None: ...
```

`local_static` is the `deploy` free/mock implementation: writes `dist/` and serves it locally. It keeps the
whole build+deploy path testable offline, exactly like the studio's `MockProvider`.

## 2. Registry refactor (replace the `if/elif` chain)

```python
# providers/registry.py
_REGISTRY: dict[tuple[str, str], Callable[[Settings], Provider]] = {}

def register(category: str, name: str):
    def deco(factory):
        _REGISTRY[(category, name)] = factory
        return factory
    return deco

def get_provider(category: str, settings: Settings | None = None) -> Provider:
    s = settings or get_settings()
    if s.provider_mode == "mock":
        return validate_provider(MockProvider(name="mock"))
    if s.provider_mode == "free":
        return validate_provider(_FREE_DEFAULTS[category](s))
    name = getattr(s, _PROVIDER_FIELDS[category])
    try:
        return validate_provider(_REGISTRY[(category, name)](s))
    except KeyError as exc:
        raise NotImplementedError(
            f"Provider '{name}' is not implemented for category '{category}'."
        ) from exc
```

Keep `provider_mode` semantics verbatim. Adding a provider becomes a new file plus a decorator — never an
edit to core. `_FREE_DEFAULTS` must exist for every category so tests never touch the network.

## 3. Agent runtime evolution (small, additive)

Keep `Agent.execute(context: dict) -> dict` untouched. Add per-step metadata in the registry:
`output_schema` (Pydantic), `validators: list[Callable]`, `max_retries` (default 2), `repair_prompt`
(validator errors fed back), `cost_budget_micros`, `idempotency_key`. The runtime writes one
`LLMInvocation` row per provider call.

Repair loop: validate -> on failure retry once with the validator error appended -> on second failure raise
`AgentContractError`, persist the raw output for inspection, pipeline enters `FAILED`.
**Never silently accept a partially valid LLM output.** The studio's "failures are not swallowed" property is
the correct model; extend it to content validity, not just exceptions.

## 4. Orchestration

v1: synchronous use cases driven from the API, with `AgentRun` rows as the durable execution record, plus one
background worker for the long steps (build, deploy, smoke test). The dashboard polls job status.

**Do not add Celery/Redis in v1.** Adopt Temporal only when you genuinely need multi-hour resumable,
retryable, parallel workflows across many clients — i.e. when the `AgentRun` table has demonstrably stopped
being sufficient evidence of what happened. Until then a queue is pure operational cost.

## 5. Repository structure

```
ai-web-agency/
├─ apps/api/src/agency/
│  ├─ api/{routes,schemas}/        # HTTP boundary + Pydantic schemas
│  ├─ application/                 # use cases (intake, approve, build, publish)
│  ├─ services/                    # intake, research, content, design, seo,
│  │                               # sitegen, build_gate, deploy, leads, agent
│  ├─ domain/                      # pipeline_definition, taxonomy, compliance rules
│  ├─ runtime/                     # agent_contract, agent_runtime, invocation log
│  ├─ providers/                   # contract, registry, llm_*, research_*,
│  │                               # deploy_local_static, deploy_vercel, notify_*
│  └─ models/                      # SQLAlchemy models + mixins
├─ apps/dashboard/                 # internal Next.js dashboard (reuses contracts)
├─ sites/
│  ├─ _template-base/              # THE one production template (Next.js, SSG)
│  └─ _presets/                    # design token presets (json)
├─ packages/contracts/             # generated JSON Schema + TS types (never hand-edited)
├─ scripts/                        # export_contracts.py, fanout_rebuild.py
└─ docs/                           # these documents + ADRs + runbooks
```

Two rules that keep this structure honest: `packages/contracts` is **generated** (Pydantic ->
`model_json_schema()` -> `json-schema-to-typescript`), and `services/` never imports a provider directly —
only through `get_provider()`.
