# Pipeline, Build Gate, Rework Paths

## 1. Pipeline definition (studio shape, new states)

```python
# src/agency/domain/pipeline_definition.py
PIPELINE_STATES: frozenset[str] = frozenset({
    "INTAKE",
    "FACTS_EXTRACTED", "FACTS_APPROVED",
    "RESEARCHING", "RESEARCH_COMPLETE", "RESEARCH_APPROVED",
    "CONTENT_GENERATING", "CONTENT_COMPLETE", "CONTENT_APPROVED",
    "DESIGNING", "DESIGN_COMPLETE", "DESIGN_APPROVED",
    "BUILDING", "BUILD_COMPLETE", "BUILD_FAILED",
    "PREVIEW_READY", "PREVIEW_APPROVED",
    "PUBLISHING", "LIVE", "MAINTENANCE",
    "FAILED",
})

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "INTAKE":             frozenset({"FACTS_EXTRACTED"}),
    "FACTS_EXTRACTED":    frozenset({"FACTS_APPROVED"}),
    "FACTS_APPROVED":     frozenset({"RESEARCHING"}),
    "RESEARCHING":        frozenset({"RESEARCH_COMPLETE"}),
    "RESEARCH_COMPLETE":  frozenset({"RESEARCH_APPROVED"}),
    "RESEARCH_APPROVED":  frozenset({"CONTENT_GENERATING", "DESIGNING"}),
    "CONTENT_GENERATING": frozenset({"CONTENT_COMPLETE", "FAILED"}),
    "CONTENT_COMPLETE":   frozenset({"CONTENT_APPROVED"}),
    "CONTENT_APPROVED":   frozenset({"DESIGNING"}),
    "DESIGNING":          frozenset({"DESIGN_COMPLETE", "FAILED"}),
    "DESIGN_COMPLETE":    frozenset({"DESIGN_APPROVED"}),
    "DESIGN_APPROVED":    frozenset({"BUILDING"}),
    "BUILDING":           frozenset({"BUILD_COMPLETE", "BUILD_FAILED"}),
    "BUILD_COMPLETE":     frozenset({"PREVIEW_READY", "FAILED"}),
    "PREVIEW_READY":      frozenset({"PREVIEW_APPROVED", "CONTENT_GENERATING", "DESIGNING"}),
    "PREVIEW_APPROVED":   frozenset({"PUBLISHING"}),
    "PUBLISHING":         frozenset({"LIVE", "FAILED"}),
    "LIVE":               frozenset({"MAINTENANCE", "PUBLISHING"}),
    "MAINTENANCE":        frozenset({"BUILDING", "PUBLISHING"}),
}

APPROVAL_CONTRACT: dict[str, tuple[str, str]] = {
    "FACTS":    ("FACTS_EXTRACTED",   "FACTS_APPROVED"),
    "RESEARCH": ("RESEARCH_COMPLETE", "RESEARCH_APPROVED"),
    "CONTENT":  ("CONTENT_COMPLETE",  "CONTENT_APPROVED"),
    "PUBLISH":  ("PREVIEW_READY",     "PREVIEW_APPROVED"),
}
```

Four gates. `PREVIEW_READY -> CONTENT_GENERATING` is the rework edge: copy rejected at preview loops back
**without** losing research or design work. `LIVE -> PUBLISHING` is the maintenance edge (client-requested
change, new `build_hash`, new approval).

Autonomy later = `Org.required_approvals` shrinking from all four to `{"PUBLISH"}`, then to none for trusted
clients. That is a config change plus an audit trail — not a rewrite.

## 2. Build gate — what makes "AI doesn't blindly ship" true

`BUILD_COMPLETE` requires **all** checks recorded as `build_validations` rows against that exact `build_hash`:

| Check | Kind | Fail |
|---|---|---|
| `content_schema` | Pydantic/Ajv validation of content model | block |
| `facts_provenance` | every published fact maps to an approved `client_fact` | block |
| `claims_policy` | banned-claim scan (medical/legal/superlative) per jurisdiction | block |
| `required_legal_pages` | Impressum + Datenschutz present (DE) | block |
| `typecheck` + `next_build` | deterministic build | block |
| `linkcheck` | no 404s, no dead anchors | block |
| `a11y_budget` | axe-core serious/critical = 0 | block |
| `perf_budget` | Lighthouse mobile perf/a11y/SEO >= 95 | warn, then block |
| `playwright_smoke` | pages 200, form POST works, zero console errors | block |
| `seo_manifest` | sitemap/robots/JSON-LD/llms.txt present + valid | block |

Publishing without a passing validation set for that `build_hash` must **raise**, not warn. This gate is the
single highest-value engineering artifact in the product: it is what lets you put AI output in front of a
paying client, and it is also your sales demo ("every site we ship passes 10 automated gates").

## 3. Gate placement rule (avoid the two classic extremes)

- Too few gates: AI garbage reaches a client's live domain; trust destroyed on client #1.
- Too many gates: nobody uses the system; you go back to hand-building sites.

v1 rule: **4 approvals, 10 automated checks, zero manual QA steps.** Approval is for *judgement* (facts,
tone, design, publish). Checks are for *correctness* (schema, links, a11y, build). Never ask a human to
verify something a script can verify.
