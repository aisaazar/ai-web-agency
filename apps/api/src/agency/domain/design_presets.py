"""Design presets the shared static template can build.

`sites/_presets/<id>.json` is the source of truth for a selectable art direction. The set is
deliberately small and closed: intake persists the client's gallery selection as a fact, the design
service writes it into the design artifact and the build service compiles it into the site's design
tokens. A preset the pipeline cannot compile must therefore be rejected at every one of those
boundaries, and the boundaries must never disagree about which presets exist.
"""

from __future__ import annotations

#: Preset used when a client never selected one (pre-existing default behaviour).
DEFAULT_DESIGN_PRESET_ID = "health"

#: Intake fact key that carries the client's template gallery selection.
SELECTED_PRESET_FACT_KEY = "selected_preset_id"

#: Closed set of presets that have a token file under `sites/_presets/`.
SUPPORTED_DESIGN_PRESET_IDS: tuple[str, ...] = ("health", "corporate", "warm")


def is_supported_design_preset(value: object) -> bool:
    """True only for a preset id the shared template knows how to compile."""
    return isinstance(value, str) and value in SUPPORTED_DESIGN_PRESET_IDS
