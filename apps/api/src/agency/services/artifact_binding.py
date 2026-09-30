"""Client-binding rules for workflow artifacts.

Artifacts are scoped to an organisation (``org_id``), never to a client, so nothing at the database
level stops one client's artifact from being fed into another client's pipeline inside the same
organisation. Every workflow action that consumes a caller-supplied artifact id must therefore prove
that the artifact belongs to the client named in the request.

An artifact resolves to its client through one of two channels:

- the artifact's own payload carries ``client_id`` (``business_facts``, ``research_report``,
  ``design_plan``, ``site_build``), or
- the artifact is derived from another artifact through ``input_artifact_id`` (``content_model``
  points at the approved ``business_facts`` revision it was generated from).

``content_model`` is the important case: the rendered content contract has no ``client_id`` field by
design (``domain/content_model.py``), so its ownership can only be proven by following the provenance
chain back to the approved facts it was generated from.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Artifact

# A provenance chain is short (facts -> content -> revisions); anything longer is corruption.
_MAX_PROVENANCE_DEPTH = 8


def artifact_client_id(session: Session, *, org_id, artifact: Artifact | None) -> str | None:
    """Resolve the owning client id of an artifact, or ``None`` when it cannot be established."""
    current = artifact
    for _ in range(_MAX_PROVENANCE_DEPTH):
        if current is None:
            return None
        client_id = (current.payload_json or {}).get("client_id")
        if isinstance(client_id, str) and client_id:
            return client_id
        if current.input_artifact_id is None:
            return None
        current = session.scalar(select(Artifact).where(
            Artifact.id == current.input_artifact_id,
            Artifact.org_id == org_id,
        ))
    return None


def belongs_to_client(session: Session, *, org_id, artifact: Artifact | None, client_id) -> bool:
    """True only when the artifact provably belongs to ``client_id``."""
    resolved = artifact_client_id(session, org_id=org_id, artifact=artifact)
    return resolved is not None and resolved == str(client_id)
