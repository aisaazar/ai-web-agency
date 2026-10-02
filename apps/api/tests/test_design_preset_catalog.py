"""The preset catalog is a contract between the API, the shared template and the dashboard.

`sites/_presets/<id>.json` is the source of truth. The API rejects anything outside it at intake
and at design time, and the dashboard mirrors the same closed set so the operator can never pick a
preset the pipeline would refuse. These tests fail if any of the three ever drift apart, which is
the failure mode that would otherwise only surface as a rejected action mid-demo.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from agency.domain.design_presets import (
    DEFAULT_DESIGN_PRESET_ID,
    SUPPORTED_DESIGN_PRESET_IDS,
    is_supported_design_preset,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PRESET_DIR = REPO_ROOT / "sites" / "_presets"
DASHBOARD_PRESET_MODULE = (
    REPO_ROOT / "apps" / "dashboard" / "src" / "lib" / "design-presets.ts"
)

# `export const DESIGN_PRESETS = ["a", "b"] as const;`
_DASHBOARD_LIST = re.compile(r"DESIGN_PRESETS\s*=\s*\[(.*?)\]", re.DOTALL)
_STRING_LITERAL = re.compile(r"""["']([^"']+)["']""")


def _presets_on_disk() -> set[str]:
    return {path.stem for path in PRESET_DIR.glob("*.json")}


def _dashboard_presets() -> list[str]:
    source = DASHBOARD_PRESET_MODULE.read_text(encoding="utf-8")
    match = _DASHBOARD_LIST.search(source)
    assert match, "the dashboard preset catalog could not be parsed"
    return _STRING_LITERAL.findall(match.group(1))


def test_api_catalog_matches_the_preset_files_on_disk():
    assert set(SUPPORTED_DESIGN_PRESET_IDS) == _presets_on_disk(), (
        "a preset was added to or removed from sites/_presets without updating the API catalog"
    )


def test_dashboard_catalog_matches_the_api_catalog():
    assert _dashboard_presets() == list(SUPPORTED_DESIGN_PRESET_IDS), (
        "the dashboard offers a different preset set than the API accepts; a client could pick a "
        "style at intake that the design step then rejects"
    )


def test_default_preset_is_part_of_the_catalog():
    assert DEFAULT_DESIGN_PRESET_ID in SUPPORTED_DESIGN_PRESET_IDS
    assert is_supported_design_preset(DEFAULT_DESIGN_PRESET_ID)


def test_dashboard_preset_labels_cover_every_preset():
    """Every offered preset needs a label, or the operator sees an empty option."""
    source = DASHBOARD_PRESET_MODULE.read_text(encoding="utf-8")
    for preset in SUPPORTED_DESIGN_PRESET_IDS:
        assert f"{preset}:" in source, f"preset {preset} has no dashboard label"


def test_preset_files_declare_tokens():
    """A preset is only selectable if it actually carries the tokens the build compiles."""
    for preset in SUPPORTED_DESIGN_PRESET_IDS:
        payload = json.loads((PRESET_DIR / f"{preset}.json").read_text(encoding="utf-8"))
        assert payload, f"preset {preset} is empty"
