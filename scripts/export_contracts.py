#!/usr/bin/env python
"""Export generated contracts: Pydantic -> JSON Schema (ADR-004).

One direction only: `apps/api/src/agency/domain/content_model.py` is the source of truth, this
script and `scripts/emit-contract-types.mjs` produce the artifacts in `packages/contracts/`.
Never hand-edit the generated files.

Usage:
    python scripts/export_contracts.py           # write/update the schema
    python scripts/export_contracts.py --check   # fail if the schema is out of date (drift check)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api" / "src"))

from agency.domain.content_model import CONTENT_SCHEMA_VERSION, ContentModel  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "packages" / "contracts" / "content.schema.json"
SCHEMA_ID = "ai-web-agency/contracts/content.schema.json"


def build_schema() -> dict[str, object]:
    schema = ContentModel.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = SCHEMA_ID
    schema["$comment"] = (
        "Generated from apps/api/src/agency/domain/content_model.py - DO NOT EDIT. "
        f"Content schema version: {CONTENT_SCHEMA_VERSION}. Regenerate with: npm run contracts"
    )
    return schema


def render_schema() -> str:
    # sorted keys + fixed indent + LF: byte-identical output for identical input (ADR-004/ADR-013).
    return json.dumps(build_schema(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    payload = render_schema()
    relative = SCHEMA_PATH.relative_to(REPO_ROOT).as_posix()
    current = SCHEMA_PATH.read_text(encoding="utf-8") if SCHEMA_PATH.exists() else None

    if current == payload:
        print(f"unchanged {relative}")
        return 0

    if check_only:
        print(f"STALE {relative}: regenerate with `npm run contracts`", file=sys.stderr)
        return 1

    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(payload, encoding="utf-8", newline="\n")
    print(f"{'wrote' if current is None else 'updated'} {relative} (content schema {CONTENT_SCHEMA_VERSION})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
